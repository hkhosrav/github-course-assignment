# Import modules
from .common import *
try:
    import simplejson as json
except ImportError:
    import json


class CourseConfig(object):
    """
    An instance of the course configuration file typically stored on the local machine.
    """

    def __init__(self, path_config):
        """
        Instantiates the CourseConfig method and loads the course config file into memory.
        :param path_config: The path to the local configuration file.
        :returns
        """

        # Load the config file
        try:
            with open(path_config, 'r') as f:
                self.config = json.load(f)
                print_status('OKAY', 'CourseConfig loaded information from local config file.')
        except FileNotFoundError:
            print_status('FAIL', 'CourseConfig unable to load local config file as it cannot be found.')
            raise
        except Exception as e:
            print_status('FAIL', 'CourseConfig encountered an error loading the local config file.')
            print(e)
            raise

        ###########################
        # Set the local variables #
        ###########################

        # Organisation info
        self.name_organisation = self.config['org']
        self.repo_org_username = self.config['org_username']
        self.token_github_api = self.config['github_api_token']

        # Prefix
        self.name_prefix = self.config['prefix']

        # Repository Info
        self.name_repo_instructors = self.config['prefix'] + '_' + self.config['repo_instructors']
        self.name_repo_updates = self.config['repo_update_branch']

        # Construct team names
        self.name_team_instructors = self.config['prefix'] + '_' + self.config['team_instructors']
        self.name_team_students = self.config['prefix'] + '_' + self.config['team_students']
        self.list_team_names = [self.name_team_instructors, self.name_team_students]

        # Assessment and student information
        self.path_assessment_status = self.config['repo_instructors_path_config'] + '/assessment_status.json'
        self.path_assessment_config = self.config['repo_instructors_path_config'] + '/assessment_config.json'
        self.path_student_mapping = self.config['repo_instructors_path_config'] + '/student_mapping.csv'
