# Import modules
from .common import *
try:
    import simplejson as json
except ImportError:
    import json


class StudentObjects(object):

    def __init__(self, GitHubConnector, CourseConfig, AssessmentConfig):

        # Load instantiated classes
        self.GH = GitHubConnector
        self.CC = CourseConfig
        self.AC = AssessmentConfig

        # Attempt to load the CSV mapping if it exists
        # Load the mapping only if the instructors repository has been initialised
        if self.CC.name_repo_instructors in self.GH.repos:
            self.dict_mapping = self.load_student_mapping()
            self.dict_groups = self.load_assessment_groups()
        else:
            self.dict_mapping = None
            self.dict_groups = None
            print_status('NOTE', 'StudentObjects has nothing to load, instructors repo has not yet been created.')

    def load_student_mapping(self):
        """
        Loads the student mapping CSV from the instructors repository and saves it as a dictionary.
        """

        file_contents = self.GH.get_file_contents(self.CC.name_repo_instructors, self.CC.path_student_mapping)

        if file_contents:
            dict_out = dict()
            for row in file_contents.splitlines()[1:]:
                cell = row.split(',')
                dict_out[cell[1]] = cell[0]
            print_status('OKAY', 'StudentObjects found student CSV mapping in the instructors repo.')
            return dict_out
        else:
            print_status('WARN', 'StudentObjects did not find student CSV mapping in the instructors repo.')
            return None

    def load_assessment_groups(self):
        """

        :return: A dictionary
        """

        # Iterate over each item of assessment
        if self.AC.json_config:
            dict_groups_out = dict()
            for a_name, a_conf in self.AC.json_config.items():

                # Extract the groups file if it exists
                cur_path = '%s/groups.json' % a_conf['main-dir']
                file_contents = self.GH.get_file_contents(self.CC.name_repo_instructors, cur_path)

                if file_contents:
                    dict_groups_out[a_name] = json.loads(file_contents)

            print_status('OKAY', 'StudentObjects found assessment groups in the instructors repo.')
            return dict_groups_out
        else:
            print_status('WARN', 'StudentObjects did not find assessment groups in the instructors repo.')
            return dict()

    def allocate_remaining_students(self, name_assessment):
        """

        :param name_assessment:
        :return:
        """

        # Load all students in the course
        set_all_students = set([x.login for x in self.GH.teams[self.CC.name_team_students].members()])

        # Load all students in the groups.json file
        set_group_students = set()
        dict_a_group = self.dict_groups[name_assessment]
        for g_name, g_memb in dict_a_group.items():
            set_group_students = set_group_students.union(set([x for x in g_memb]))

        # Iterate over all remaining students and add them to groups.json as doing individual work
        dict_groups_out = dict_a_group
        for missing_student in set_all_students - set_group_students:
            if missing_student not in dict_a_group:
                dict_groups_out[missing_student] = [missing_student]
            else:
                print("Something has gone wrong, the student is in the groups file but wasn't detected.")
                1/0 # TODO; throw an error

        # Save the modified groups.json file
        if len(set_all_students - set_group_students) > 0:
            out_json = json.dumps(dict_groups_out, indent=4)
            cur_path = '%s/groups.json' % self.AC.json_config[name_assessment]['main-dir']
            self.GH.create_file(name_repo=self.CC.name_repo_instructors,
                                path_file=cur_path,
                                file_content=out_json,
                                overwrite=True)

            # Set the updated groups
            self.dict_groups[name_assessment] = dict_groups_out
            print_status('OKAY', 'Allocated remaining students not in groups to individual work.')

    def import_students_csv(self, csv_input):
        """

        :param csv_input:
        :return:
        """

        # Store in the instructors repository if valid
        if validate_csv(csv_input):

            # Save to instructors repository
            self.GH.create_file(name_repo=self.CC.name_repo_instructors, path_file=self.CC.path_student_mapping,
                                file_content=csv_input, overwrite=True)

            # Read contents of CSV file, skip first row (header)
            list_lines = csv_input.splitlines()
            list_cells = [row.split(',') for row in list_lines]
            list_username = [cell[1] for cell in list_cells[1:]]

            for username in list_username:
                # Invite to the students team (specified in the course config file)
                self.GH.invite_username_to_team(name_user=username, name_team=self.CC.name_team_students)

            # Reload the student mapping
            self.dict_mapping = self.load_student_mapping()

    def import_assessment_groups_csv(self, name_assessment, csv_input):
        """

        :param name_assessment:
        :param csv_input:
        :return:
        """

        # Check prerequisite
        if name_assessment not in self.AC.json_config:
            print_status('FAIL', 'Assessment has not yet been configured, see [configure_assessment].')
            return False

        # Check group size
        max_group_size = self.AC.json_config[name_assessment]['max-group-size']
        if max_group_size <= 1:
            print_status('SKIP', 'Assessment not configured for group work, see [max-group-size] setting.')
            return False

        # Validate the CSV
        if not validate_csv(csv_input, delimiter='|'):
            print_status('FAIL', 'CSV format is invalid.')

        # Convert the CSV into a dictionary of lists
        dict_groups = dict()
        list_all_members = list()
        for idx, row in enumerate(csv_input.splitlines()):
            if idx > 0:
                group_name = row.split('|')[0]

                # Extract the members
                list_cur_g_members = [x.strip() for x in row.split('|')[1].split(',')]

                # Check to make sure group name is unique
                if group_name in dict_groups:
                    print_status('FAIL', 'Group name is not unique: %s' % group_name)
                    return False

                # Perform individual level checks
                for cur_username in list_cur_g_members:

                    # User is only in one group
                    if cur_username in list_all_members:
                        print_status('FAIL', 'User is in more than one group: %s' % cur_username)
                        return False

                    # User is a part of the org
                    elif not self.GH.teams[self.CC.name_team_students].is_member(cur_username):
                        print_status('FAIL', 'User not part of the student team, no changes have been made: %s' % cur_username)
                        return False

                    # Maximum members in a group
                    elif len(list_cur_g_members) > max_group_size:
                        print_status('FAIL', 'Group exceeds maximum number of allowed members: %s' % group_name)

                # Save - for group uniqueness checks
                list_all_members = list_all_members + list_cur_g_members

                # Finally, save the members to the group
                dict_groups[group_name] = list_cur_g_members

        # Save the JSON
        json_out = json.dumps(dict_groups, indent=4)

        ######################
        # Store as JSON file #
        ######################

        write_path = '%s/groups.json' % self.AC.json_config[name_assessment]['main-dir']
        self.GH.create_file(name_repo=self.CC.name_repo_instructors, path_file=write_path,
                            file_content=json_out, overwrite=True, branch='master')

        ############################
        # Update the group mapping #
        ############################

        self.dict_groups = self.load_assessment_groups()

    def prepare_repo(self, name_assessment, name_target_branch, overwrite):
        """

        :param name_assessment:
        :param name_target_branch:
        :param overwrite:
        :return:
        """

        # Load all assessment files
        source_a_dir = self.AC.json_config[name_assessment]['main-dir']
        source_a_contents = self.GH.get_all_files_in_repo_at_path(name_repo=self.CC.name_repo_instructors,
                                                                  path=source_a_dir)

        # Process each group
        for group_name in self.dict_groups[name_assessment]:

            print('Processing group: %s' % group_name)

            # Build the group repository name from the group_name
            group_a_repo_name = self.CC.name_prefix + '_' + name_assessment + '_' + group_name

            # Create the assessment repository
            self.GH.create_repository(group_a_repo_name, is_private=True)

            # Add the teaching team as a collaborator with read access
            self.GH.add_collaborator_team_to_repo(name_team=self.CC.name_team_instructors,
                                                  name_repo=group_a_repo_name,
                                                  permission='pull')

            # Iterate over each file to be copied
            for filename, file_contents_object in source_a_contents.items():

                # Don't copy the groups.json file across
                if filename != 'groups.json':
                    self.GH.create_file(name_repo=group_a_repo_name, path_file=filename,
                                        file_content=file_contents_object, branch=name_target_branch,
                                        overwrite=overwrite)

            # Create the updates branch if it does not already exist
            self.GH.create_branch(name_repo=group_a_repo_name, name_new_branch=self.CC.name_repo_updates)

            # Enable branch protection
            restrictions = {'users': [self.CC.repo_org_username], 'teams': [self.CC.name_team_instructors]}
            self.GH.protect_branch(name_repo=group_a_repo_name, name_branch=self.CC.name_repo_updates, restrictions=restrictions)

            print('\n')
