# Import modules
from .common import *
try:
    import simplejson as json
except ImportError:
    import json


class AssessmentConfig(object):

    def __init__(self, GH, CourseConf):
        """
        Instantiates the module, attempts to load the configuration file.
        """

        ###################
        # Local variables #
        ###################

        # Load instantiated classes
        self.GH = GH
        self.CC = CourseConf

        # Load the configuration JSON only if the instructors repository has been initialised
        if self.CC.name_repo_instructors in self.GH.repos:
            self.json_config = self.load_config()
            self.json_status = self.load_status()
        else:
            self.json_config = None
            self.json_status = None
            print_status('NOTE', 'AssessmentConfig has nothing to load, instructors repo has not yet been created.')

    def load_config(self):
        """
        Attempts to load the latest copy of the assessment configuration file from the instructors repository.
        :return: json of the configuration file or None.
        """

        file_contents = self.GH.get_file_contents(self.CC.name_repo_instructors, self.CC.path_assessment_config)

        if file_contents:
            print_status('OKAY', 'AssessmentConfig loaded assessment information from the instructors repo.')
            return json.loads(file_contents)
        else:
            print_status('WARN', 'AssessmentConfig did not find any assessment information in the instructors repo.')
            return None

    def load_status(self):
        """
        Attempts to load the latest copy of the assessment status file from the instructors repository.
        :return: JSON of the status file or None.
        """

        file_contents = self.GH.get_file_contents(self.CC.name_repo_instructors, self.CC.path_assessment_status)

        if file_contents:
            print_status('OKAY', 'AssessmentConfig loaded status information from the instructors repo.')
            return json.loads(file_contents)
        else:
            print_status('WARN', 'AssessmentConfig did not find any status information in the instructors repo.')
            return None

    def update_config(self, obj_json):
        """
        Updates the assessment configuration with the input given. Prohibits changing min-dir.
        :param obj_json: (json object)
        :return: The updated configuration or None.
        """

        # Remove spaces from the assessment name
        obj_json_out = dict()
        for a_name, a_dict in obj_json.items():
            cur_a_name_parsed = a_name.replace(' ', '_')
            obj_json_out[cur_a_name_parsed] = a_dict

        # Check to see if a change to the main-dir parameter has been made, if the assessment already existed
        if self.json_config:
            for cur_a in obj_json_out:
                if cur_a in self.json_config:
                    if self.json_config[cur_a]['main-dir'] != obj_json_out[cur_a]['main-dir']:
                        print_status('FAIL', 'AssessmentConfig cannot change the assessment main-dir. '
                                             'No changes have been made.')
                        return None

        # Save the assessment configuration file
        self.GH.create_file(name_repo=self.CC.name_repo_instructors,
                            path_file=self.CC.path_assessment_config,
                            file_content=json.dumps(obj_json_out, indent=4),
                            overwrite=True,
                            branch='master')

        # Save the updated JSON
        self.json_config = obj_json_out

        # Refresh the assessment status
        self.update_status()

    def update_status(self, a_name=None, a_status=None):
        """
        Updates the assessment status file and refreshes the markdown readme in the instructors repository.
        If either a_name or a_status is None then a refresh is done.
        :param str a_name: (optional) The name of the item of assessment as listed in the assessment config.
        :param str a_status: (optional) The status of the assessment.
        """

        # Targeted update of json_status
        if a_name and a_status:
            json_status_out = self.json_status
            json_status_out[a_name] = a_status
            print_status('OKAY', 'Assessment (%s) status set to: %s' % (a_name, a_status))

        # Refresh all
        else:
            json_status_out = dict()
            for status_a_name in self.json_config.keys():
                if self.json_status:
                    if status_a_name in self.json_status.keys():
                        json_status_out[status_a_name] = self.json_status[status_a_name]
                    else:
                        json_status_out[status_a_name] = 'Unprepared'
                else:
                    json_status_out[status_a_name] = 'Unprepared'
            print_status('OKAY', 'All assessment status names refreshed using config file.')

        # Save the assessment status file
        self.GH.create_file(name_repo=self.CC.name_repo_instructors,
                            path_file=self.CC.path_assessment_status,
                            file_content=json.dumps(json_status_out, indent=4),
                            overwrite=True,
                            branch='master')

        # Save the updated JSON
        self.json_status = json_status_out

        #######################
        # Update the markdown #
        #######################

        # Create an array for the markdown table
        list_rows = [['Name', 'Status']]
        for a_name, a_status in self.json_status.items():
            if a_status.lower() == 'closed':
                list_rows.append([a_name, '[Closed](grading/%s/README.md)' % a_name])
            else:
                list_rows.append([a_name, a_status])

        # Generate markdown from the array
        str_md = '# %s - Instructors\n## Assessment status\n%s' % (self.CC.name_prefix, array_to_md_table(list_rows))

        # Override the contents of the README.md file
        self.GH.create_file(name_repo=self.CC.name_repo_instructors,
                            path_file='README.md',
                            file_content=str_md,
                            overwrite=True,
                            branch='master')
