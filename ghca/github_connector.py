# Import modules
from .common import *
import github3
import base64
try:
    import simplejson as json
except ImportError:
    import json
import os
from datetime import datetime
from github3.models import __timeformat__ as gh3_time_fmt
from io import BytesIO
import zipfile


class GitHubConnector(object):

    def __init__(self, CourseConf):

        # Load instantiated classes
        self.CC = CourseConf

        # Login to GitHub using the API
        try:
            self.GH = github3.login(token=self.CC.token_github_api)
        except github3.exceptions.AuthenticationFailed:
            print_status('FAIL', 'GitHubConnector unable to authenticate, bad API token/credentials')
            raise
        except Exception as e:
            print_status('FAIL', 'GitHubConnector encountered an exception.')
            print(e)
            raise

        # Extract organisation objects
        self.org = self.GH.organization(self.CC.name_organisation)
        self.teams = {team.name: team for team in self.org.teams()}
        self.repos = {repo.name: repo for repo in self.org.repositories()}
        print_status('OKAY', 'GitHubConnector successfully authenticated.')

    def create_team(self, name_team, privacy='secret', permission='pull'):
        """
        Creates a new team.
        :param name_team:self, name, repo_names=[], privacy='secret', permission='pull'
        :param privacy:
        :param permission:
        :return:
        """

        if name_team in self.teams:
            print_status('SKIP', 'Team already exists: %s.' % name_team)
        else:
            team = self.org.create_team(name=name_team, repo_names=[], privacy=privacy, permission=permission)
            if team:
                print_status('OKAY', 'Team created: %s (%s).' % (name_team, privacy))
                self.teams[name_team] = team
                return team
            else:
                print_status('FAIL', 'Team failed to create: %s.' % name_team)
                return None

    def create_repository(self, name_repo, is_private):
        """
        Creates a new repository.
        :param name_repo:
        :param is_private:
        :return: (Repo) object or None.

        """
        if name_repo in self.repos:
            print_status('SKIP', 'Repository already exists: %s.' % name_repo)
            return self.repos[name_repo]
        else:
            repo = self.org.create_repository(name_repo, private=is_private)
            if repo:
                print_status('OKAY', 'Repository created: %s (%s).' % (name_repo, 'private' if is_private else 'public'))
                self.repos[name_repo] = repo
                return repo
            else:
                print_status('FAIL', 'Repository failed to create: %s.' % name_repo)
                return None

    def get_all_files_in_repo_at_path(self, name_repo, path="", get_contents=True, relative_path=True, branch="master"):
        """
        ?
        :param repo:
        :param path:
        :param get_contents:
        :param relative_path:
        :param branch:
        :return:
        """

        repo = self.get_repo_obj(name_repo)

        if path in ["/", "."]:  # assume the caller means the root directory if these are used for path
            path = ""
        if path and path[0] != "/":  # if path non-empty, make sure it ends with "/"
            path += "/"
        data = dict()
        try:
            tree = repo.tree("%s?recursive=1" % branch)
        #except github3.exceptions.ClientError as e:
        except Exception as e:
            return dict()  # return empty dict because repository is empty
        tree = tree.as_dict()
        if tree['truncated']:
            print("Warning: there were too many files and not all were received through the GitHub API!")
        for elem in tree['tree']:
            if elem['path'].startswith(path):
                if elem['type'] == 'blob':
                    # get the actual contents
                    contents = base64.b64decode(repo.file_contents(elem['path']).content) if get_contents else elem[
                        'sha']
                    if relative_path:
                        data[elem['path'][len(path):]] = contents
                    else:
                        data[elem['path']] = contents
        return data

    def create_file(self, name_repo, path_file, file_content, overwrite=False, branch='master'):
        """
        ??
        :param name_repo:
        :param name_file:
        :param file_content:
        :param overwrite:
        :param branch:
        :return: (string) Contents of the file after modification.
        """

        # Parse path information
        name_base = os.path.basename(path_file)
        name_dir = os.path.dirname(path_file)

        # Load the file if it exists prior to any changes
        file_before = self.get_file_contents(name_repo, path_file, ref=branch)

        # Load all contents in the directory
        repo_contents_info = self.get_all_files_in_repo_at_path(name_repo, name_dir, False, branch=branch)

        #################
        # Sanity checks #
        #################

        if file_before:

            if not overwrite:
                print_status('SKIP', 'The file %s already exists and overwrite is set to False.' % path_file)
                return None

            elif overwrite:
                try:
                    file_content_decoded = file_content.decode('UTF-8')
                except AttributeError:
                    file_content_decoded = file_content
                except UnicodeDecodeError:
                    file_content_decoded = file_content
                if file_before == file_content_decoded:
                    print_status('SKIP', 'No new changes for the file %s.' % path_file)
                    return None

        ###################
        # Create the file #
        ###################

        # Convert to UTF-8 encoding
        if not isinstance(file_content, bytes):
            #file_content_bytes = bytes(file_content, 'UTF-8') # Not python 2.7 compatible.
            file_content_bytes = file_content.encode('UTF-8')
        else:
            file_content_bytes = file_content

        # Create the file in the repository object
        if name_base in repo_contents_info:
            file_sha = repo_contents_info[name_base]
        else:
            file_sha = None
        repo_obj = self.get_repo_obj(name_repo)
        repo_obj.create_file(path=path_file,
                             message='Update %s.' % name_base,
                             content=file_content_bytes,
                             sha=file_sha,
                             branch=branch)

        #################################
        # Validate the file was changed #
        #################################

        file_after = self.get_file_contents(name_repo, path_file, ref=branch)

        if file_after != file_before:
            print_status('OKAY', 'File %s was successfully changed.' % path_file)
            return file_after
        else:
            print_status('FAIL', 'An issue was encountered when updating the contents of the file %s.' % path_file)
            return None

    def add_collaborator_team_to_repo(self, name_team, name_repo, permission):
        """
        Adds a team as a collaborator to a repository.
        :param name_team:
        :param name_repo:
        :param permission:
        :return: Boolean
        """

        if name_repo not in self.repos:
            print_status('FAIL', 'Team (%s) cannot be added to repository (%s) as it cannot be found.' % (name_team, name_repo))
            return False
        else:
            obj_team = self.get_team_obj(name_team)
            obj_repo = self.get_repo_obj(name_repo)

            if obj_team.add_repository(obj_repo, permission):
                print_status('OKAY', 'Team (%s) added to (%s) (%s).' % (name_team, name_repo, permission))
                return True
            else:
                print_status('FAIL', 'Team (%s) failed to be added to repo (%s).' % (name_team, name_repo))
                return False

    def add_collaborator_to_repo(self, name_repo, name_user, permission):

        repo = self.get_repo_obj(name_repo)

        if repo is None:
            print_status('FAIL', 'Collaborator (%s) could not be added to repo (%s) as it is none.' % (name_user, name_repo))
            return False

        if not self.org.is_member(name_user):
            print_status('WARN', '%s is not a member of the %s organisation. Proceeding anyway.' % (name_user, self.org.name))

        if repo.name not in self.repos:
            print_status('FAIL', 'Could not find repo: %s' % name_repo)
            return False

        if repo.add_collaborator(name_user, permission=permission):
            print_status('OKAY', 'Added %s to %s with %s permission.' % (name_user, name_repo, permission))
            return True
        else:
            print_status('FAIL', 'Unable to add %s to: %s (possibly as they have not accepted)' % (name_user, repo.name))
            return False

    def get_team_obj(self, name_team):
        """
        Loads a team object from the list of teams.
        :param name_team:
        :return:
        """

        if name_team not in self.teams:
            print_status('FAIL', 'The team %s does not exist within the organisation.' % name_team)
        else:
            return self.teams[name_team]

    def get_repo_obj(self, name_repo):
        """
        Loads a repository from the list of repository objects.
        :param name_repo: (string) The name of the repository.
        :return: repository object or None
        """

        if name_repo not in self.repos:
            print_status('FAIL', 'The repository %s does not exist within the organisation.' % name_repo)
        else:
            return self.repos[name_repo]

    def get_file_contents(self, name_repo, path_file, ref=None, decode=True):
        """
        Loads the contents of a specified file within a repository.
        :param name_repo: (string) The name of the repository the file is stored in.
        :param path_file: (string) The path to the file.
        :param ref:
        :param decode: (boolean) If the file should be decoded.
        :return: (bytes?) The contents of the file or None.
        """

        obj_repo = self.get_repo_obj(name_repo)
        if not obj_repo:
            return None
        c1 = obj_repo.file_contents(path_file, ref=ref)
        if not c1:
            return None
        c2 = base64.b64decode(c1.content)
        if not decode:
            return c2
        else:
            try:
                c3 = c2.decode("UTF-8")
                return c3
            except UnicodeDecodeError:  # this error got thrown for an image, for example.
                return c2

    def invite_username_to_team(self, name_user, name_team):
        """

        :param name_user:
        :param name_team:
        :return:
        """

        # Extract the team object
        obj_team = self.get_team_obj(name_team)

        # Check if the user is already a member of the team
        if obj_team.is_member(name_user):
            print_status('SKIP', 'User is already a member of the team %s: %s' % (name_team, name_user))
        else:
            is_org_member = self.org.is_member(name_user)
            success = obj_team.invite(name_user)
            if success and is_org_member:
                print_status('OKAY', 'User invited to team %s: %s' % (name_team, name_user))
            elif success and not is_org_member:
                print_status('OKAY', 'User invited to organisation %s and team %s: %s' % (self.org.login, name_team, name_user))
            else:
                print_status('FAIL', 'User failed to be added to team %s: %s' % (name_team, name_user))

    def create_branch(self, name_repo, name_new_branch, name_source_branch="master"):
        """

        :param repo:
        :param new_branch_name:
        :param source_branch_name:
        :return:
        """

        obj_repo = self.get_repo_obj(name_repo)
        existing_branch = obj_repo.branch(name_new_branch)
        if existing_branch:
            print_status('SKIP', 'Branch (%s) already exists in repo: %s' % (name_new_branch, name_repo))
            return existing_branch

        # Get the revision SHA and encode the response as JSON
        obj_branch = obj_repo.branch(name_source_branch)
        latest_sha = obj_branch.latest_sha().decode('UTF-8')
        json_latest_sha = json.loads(latest_sha)

        # create branch
        new_ref = obj_repo.create_ref(ref="refs/heads/%s" % name_new_branch, sha=json_latest_sha['sha'])
        if new_ref:
            print_status('OKAY', 'Branch (%s) created in repo: %s' % (name_new_branch, name_repo))
            return obj_repo.branch(name_new_branch)
        else:
            print_status('FAIL', 'Branch (%s) failed to create in repo: %s' % (name_new_branch, name_repo))
            return None

    def protect_branch(self, name_repo, name_branch, required_status_checks=None, restrictions=None,
                required_pull_request_reviews=None, enforce_admins=False):
        """

        :param name_repo:
        :param name_branch:
        :param required_status_checks:
        :param restrictions:
        :param required_pull_request_reviews:
        :param enforce_admins:
        :return:
        """

        repo = self.get_repo_obj(name_repo)
        protected = repo.branch(name_branch).protect(required_status_checks=required_status_checks,
                                                           restrictions=restrictions,
                                                           required_pull_request_reviews=required_pull_request_reviews,
                                                           enforce_admins=enforce_admins)
        if protected:
            print_status('OKAY', 'Branch has been protected: %s' % name_branch)
        else:
            print_status('FAIL', 'Branch failed to be protected: %s' % name_branch)

    def create_pull_request(self, name_repo, title, body, branch):
        """

        :param name_repo:
        :param title:
        :param body:
        :param branch:
        :return:
        """

        repo = self.get_repo_obj(name_repo)

        if not repo.branch(branch):
            print_status('FAIL', 'Branch %s does not exist, therefore a PR cannot be created. Aborting.' % branch)

        # if the pull request already exists, update it
        for existing_PR in repo.pull_requests(state="open"):
            if existing_PR.as_dict()["title"] == title:
                print_status('WARN', 'An open pull request with title "%s" in repo %s already exists.' % (title, name_repo))

                if existing_PR.as_dict()["head"]["sha"] == repo.branch(branch).latest_sha().decode("UTF-8"):
                    print_status('SKIP', 'The latest sha of this PR matches the latest sha of the branch %s, so this PR is vacuous (I think). Skipping.' % branch)
                    return

                PR = existing_PR.update(title=title, body=body)
                if PR:
                    print_status('OKAY', 'Successfully updated Pull Request in %s from branch %s to master.' % (name_repo, branch))
                else:
                    print_status('FAIL', 'Failed to update Pull Request in %s from branch %s to master.' % (name_repo, branch))
                return


        if next(repo.commits(sha=branch, number=1)) in repo.commits(sha="master"):
            print_status('SKIP', 'The latest commit in the %s branch is equal to that of master.' % branch)
            return

        PR = repo.create_pull(title=title, base="master", head=branch, body=body)
        if PR:
            print_status('OKAY', 'Successfully created Pull Request in %s from branch %s to master.' % (repo.name, branch))
        else:
            print_status('FAIL', 'Failed to create Pull Request in %s from branch %s to master.' % (repo.name, branch))

    def get_commit_before_datetime(self, name_repo, utc_datetime, name_branch='master'):
        """

        :param name_repo:
        :param str_datetime:
        :return:
        """

        repo = self.get_repo_obj(name_repo)

        get_time_f = lambda commit: datetime.strptime(commit.commit.committer["date"], gh3_time_fmt)
        commits = list(repo.commits(sha=name_branch, until=datetime.strftime(utc_datetime, gh3_time_fmt)))
        if len(commits) > 0:
            return max(commits, key=get_time_f)
        else:
            return None

    def create_unique_issue(self, name_repo, title, labels, body, list_assignees):
        """

        :param name_repo:
        :param title:
        :param labels:
        :param body:
        :param list_assignees:
        :return:
        """

        repo = self.get_repo_obj(name_repo)

        # Check if the issue is already open
        if len(list(repo.issues(labels=labels))) > 0:
            print_status('SKIP', 'SKIP: An issue with the label(s) %s already exists.' % ','.join(labels))
        else:
            # Create the issue
            if repo.create_issue(title=title, body=body, labels=labels, assignees=list_assignees):
                print_status('OKAY', 'Successfully created the issue: %s.' % title)
            else:
                print_status('FAIL', 'Unable to create the issue: %s.' % title)

    def copy_directory(self, dir_source, name_repo_source, dir_target, ref, overwrite, name_target_branch, compress=False):
        """
        Copies the contnts from one directory to another.
        :param dir_source:
        :param dir_target:
        :param ref:
        :param overwrite:
        :return:
        """

        # Load all assessment files
        file_contents_source = self.get_all_files_in_repo_at_path(name_repo=name_repo_source,
                                                                  path=dir_source,
                                                                  branch=ref)

        # Create an in memory zip file
        if compress:
            in_memory_zip = BytesIO()
            zf = zipfile.ZipFile(in_memory_zip, "w", zipfile.ZIP_DEFLATED, False)
        else:
            in_memory_zip = None
            zf = None

        # Iterate over each file to be copied
        for filename, file_contents_object in file_contents_source.items():

            # Add to archive (if compression)
            if in_memory_zip:

                # Write the file to the in-memory zip
                zf.writestr(filename, file_contents_object)

                # Mark the files as having been created on Windows so that
                # Unix permissions are not inferred as 0000
                for zfile in zf.filelist:
                    zfile.create_system = 0

        if in_memory_zip:
            zf.close()
            self.create_file(name_repo=self.CC.name_repo_instructors, path_file='%s.zip' % dir_target,
                             file_content=in_memory_zip.getvalue(), branch=name_target_branch,
                             overwrite=overwrite)
