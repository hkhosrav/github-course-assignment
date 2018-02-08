# Import modules
from .common import *
from .assessment_config import *
from .course_config import *
from .github_connector import *
from .student_objects import *
import base64
import requests


class GitHubLink(object):
    """Initialises the GitHubLink method which will act as a master controller for all other methods."""

    def __init__(self, config_file):
        """
        :param str config_file: (required) The file path to the course configuration file, typically config/name.json.
        """

        print("  ______ __  __ __     __     _____                        ___           _                          __ ")
        print(" / ___(_) /_/ // /_ __/ /    / ___/__  __ _________ ___   / _ | ___ ___ (_)__ ____  __ _  ___ ___  / /_")
        print("/ (_ / / __/ _  / // / _ \  / /__/ _ \/ // / __(_-</ -_) / __ |(_-<(_-</ / _ `/ _ \/  ' \/ -_) _ \/ __/")
        print("\___/_/\__/_//_/\_,_/_.__/  \___/\___/\_,_/_/ /___/\__/ /_/ |_/___/___/_/\_, /_//_/_/_/_/\__/_//_/\__/ ")
        print("                                                                        /___/                          ")

        # Instantiate various classes to control different groups
        print_header('Instantiating control classes')
        self.CC = CourseConfig(config_file)
        self.GH = GitHubConnector(self.CC)
        self.AC = AssessmentConfig(self.GH, self.CC)
        self.SO = StudentObjects(self.GH, self.CC, self.AC)
        print_status('OKAY', 'Done.')

    def init_course(self):
        """
        Initialises GitHub student and instructor teams; and the instructor repository using information
        provided in the course configuration file.
        """
        print_header('Initialising GitHub objects')

        # Create student and instructor teams
        for name_team in self.CC.list_team_names:
            self.GH.create_team(name_team)

        # Create the instructor repository
        self.GH.create_repository(self.CC.name_repo_instructors, is_private=True)
        self.GH.add_collaborator_team_to_repo(self.CC.name_team_instructors, self.CC.name_repo_instructors, 'pull')
        print_status('OKAY', 'Done.')

    def configure_assessment(self, obj_json):
        """ Imports a dictionary (json) object and stores it in the instructors repository. """

        print_header('Configuring assessment')
        self.AC.update_config(obj_json)
        print_status('OKAY', 'Done.')

    def import_students_csv(self, csv_input):
        """

        :param csv_input:
        :return:
        """

        print_header('Importing students to organisation from CSV')
        self.SO.import_students_csv(csv_input)
        print_status('OKAY', 'Done.')

    def import_assessment_groups_csv(self, name_assessment, csv_input):
        """

        :param name_assessment:
        :param csv_input:
        :return:
        """

        print_header('Importing student groups for assessment: %s' % name_assessment)
        self.SO.import_assessment_groups_csv(name_assessment, csv_input)
        print_status('OKAY', 'Done.')

    def prepare_assessment(self, name_assessment, name_target_branch, overwrite):
        """

        :param name_assessment:
        :param name_target_branch:
        :param overwrite:
        :return:
        """

        print_header('Preparing assessment: %s' % name_assessment)

        # Assign any students not yet allocated in groups.json to individual work
        self.SO.allocate_remaining_students(name_assessment)

        # Iterate over each group and create a repository for the assessment
        self.SO.prepare_repo(name_assessment, name_target_branch, overwrite)

        # Update the assessment status
        if name_target_branch != self.CC.name_repo_updates:
            self.AC.update_status(a_name=name_assessment, a_status='Prepared')
            print_status('OKAY', 'Done.')

    def release_assessment(self, name_assessment, permission):
        """

        :param name_assessment:
        :param permission:
        :return:
        """

        print_header('Releasing assessment: %s' % name_assessment)

        # Check that assessment has been prepared
        if self.AC.json_status[name_assessment] == 'Unprepared':
            print_status('FAIL', 'The assessment has not yet been prepared, execute prepare_assessment first.')
        else:
            # Iterate over each group and invite the student(s) as a collaborator
            for g_name, list_mem in self.SO.dict_groups[name_assessment].items():
                name_repo = self.CC.name_prefix + '_' + name_assessment + '_' + g_name
                for g_mem in list_mem:
                    self.GH.add_collaborator_to_repo(name_repo=name_repo, name_user=g_mem, permission=permission)

            # Update the assessment status
            self.AC.update_status(name_assessment, 'Released')

        print_status('OKAY', 'Done.')

    def update_assessment_pr(self, name_assessment):
        """

        :param name_assessment:
        :return:
        """
        print_header('Updating assessment: %s' % name_assessment)

        # Iterate over each group and move modified files to the update branch
        self.SO.prepare_repo(name_assessment, self.CC.name_repo_updates, overwrite=True)

        # Create a pull request for each student
        for g_name, list_mem in self.SO.dict_groups[name_assessment].items():

            # Load info
            name_repo = self.CC.name_prefix + '_' + name_assessment + '_' + g_name
            str_members = '@' + ', @'.join(list_mem)
            title = 'An update to %s' % name_assessment
            body = '%s: the instructor has updated this assessment, %s %s, since its original form. Navigate to the `Files changed` tab to see what changed. You may want to merge this Pull Request. This is an automatically generated message.' % \
                   (str_members, self.CC.name_organisation, name_assessment)

            # Create PR
            self.GH.create_pull_request(name_repo=name_repo, title=title, body=body, branch=self.CC.name_repo_updates)
        print_status('OKAY', 'Done.')

    def close_assessment(self, name_assessment, compress):
        """
        Closes assessment and also generates the HTMl markdown table for display in the instructors repository.
        :param name_assessment:
        :return:
        """

        print_header('Closing assessment %s' % name_assessment)

        # Create an array for the markdown table
        html_table = '<table><tr><th>Group Name</th><th>Students</th><th>View Submission</th><th>Download Submission</th></tr>'

        for g_name, list_mem in self.SO.dict_groups[name_assessment].items():

            print('\nProcessing group: %s' % g_name)

            # Build the group repository name from the group_name
            name_repo = self.CC.name_prefix + '_' + name_assessment + '_' + g_name

            # Revoke permission for each student
            for g_mem in list_mem:
                self.GH.add_collaborator_to_repo(name_repo=name_repo, name_user=g_mem, permission='pull')

            # Get student username to ID mapping
            list_parse_mem = ['%s (%s)' % (mem, self.SO.dict_mapping[mem]) for mem in list_mem]
            str_members = '<br />\n'.join(list_parse_mem)

            # Get submission link
            name_repo = self.CC.name_prefix + '_' + name_assessment + '_' + g_name

            due_date_utc = str_datetime_to_utc_offset(self.AC.json_config[name_assessment]['deadline'],
                                                      self.AC.json_config[name_assessment]['deadline-utc-offset'])
            latest_commit = self.GH.get_commit_before_datetime(name_repo, due_date_utc, name_branch='master')

            # If commits were made before the deadline
            if latest_commit:

                commit_sha_full = latest_commit.sha
                commit_sha_small = latest_commit.sha[0:7]

                # Get the time of commit
                latest_commit_dt = datetime.strptime(latest_commit.commit.committer['date'], gh3_time_fmt)
                latest_commit_dt_local = str_datetime_to_utc_offset(datetime.strftime(latest_commit_dt, '%Y-%m-%d %H:%M:%S'),
                                           -self.AC.json_config[name_assessment]['deadline-utc-offset'])
                latest_commit_str_local = datetime.strftime(latest_commit_dt_local, '%Y%m%d_%H%M%S')

                self.GH.copy_directory(dir_source='/', name_repo_source=name_repo,
                                       dir_target='grading/%s/%s_%s_%s' % (name_assessment, g_name, latest_commit_str_local, commit_sha_small),
                                       ref=latest_commit.sha, overwrite=True, name_target_branch='master', compress=compress)


                # The link to the latest submission
                submit_str = '<a href="../../../../../%s/tree/%s">View</a>' % (name_repo, commit_sha_full)

                # Get the URL to the zip file just updated
                url_zip = '<a href="../../../../raw/master/grading/%s/%s_%s_%s.zip">Download</a>' % (name_assessment, g_name, latest_commit_str_local, commit_sha_small)

            else:
                submit_str = 'No commits before deadline.'
                url_zip = 'No commits before deadline.'


            # Save row
            html_table += '\n<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (g_name, str_members, submit_str, url_zip)


        # Update assessment status
        print()
        self.AC.update_status(name_assessment, 'Closed')

        # Generate markdown from the array
        html_table += '\n</html>'
        str_md = '# %s - Instructors\n## Submissions: %s\n%s' % (self.CC.name_prefix, name_assessment, html_table)
        str_md = '# %s - Instructors\n' % self.CC.name_prefix
        str_md += '## Assessment: %s\n' % name_assessment
        str_md += '### Deadline: %s\n' % self.AC.json_config[name_assessment]['deadline']
        str_md += html_table

        # Creating grading page
        self.GH.create_file(name_repo=self.CC.name_repo_instructors,
                            path_file='grading/%s/README.md' % name_assessment,
                            file_content=str_md,
                            overwrite=True)
        print_status('OKAY', 'Done.')

    def forfeit_assessment(self, name_assessment):
        """

        :param name_assessment:
        :return:
        """

        print_header('Forfeiting assessment: %s' % name_assessment)

        # Create the issue
        i_title = 'Assessment forfeit'
        i_labels = ['ownership_change']
        i_body = 'This item of assessment has been completed and ownership of the repository has been forfeit, you now have admin rights.<br /><br />'
        i_body += 'If you would like to keep a copy of your repository please navigate to the <a href="../settings/">settings</a> '
        i_body += 'menu and follow the steps below. Note that only one person can own the repository but multiple people '
        i_body += 'can still collaborate, consider who will take ownership if this was a group assessment.<br /><br />'
        i_body += '1. If you are not allowed private repositories set the repository to public, scroll to the bottom of the settings menu and the "Make Public" option in the Danger Zone.<br /><br />'
        i_body += '2. In the Danger Zone, select Transfer ownership and follow the remaining steps. '

        # Process each group
        for g_name, list_mem in self.SO.dict_groups[name_assessment].items():
            name_repo = self.CC.name_prefix + '_' + name_assessment + '_' + g_name

            # Set to admin rights
            for g_mem in list_mem:
                self.GH.add_collaborator_to_repo(name_repo=name_repo, name_user=g_mem, permission='admin')
            self.GH.create_unique_issue(name_repo, i_title, i_labels, i_body, list_mem)

        # Update status
        self.AC.update_status(name_assessment, 'Forfeit')
        print_status('OKAY', 'Done.')
