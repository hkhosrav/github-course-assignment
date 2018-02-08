# GitHub Course Assignment
A framework to deploy and administrate course assignments using GitHub's API. Developed using the development branch of the popular GitHub API library, [github3](https://github.com/sigmavirus24/github3.py).

https://github.com/hkhosrav/github-course-assignment

## Getting started
1. Clone this repository to your local machine.
2. Install the required libraries by running: `pip install -r /path/to/requirements.txt`
3. Start a Jupyter notebook session in the current directory by running: `jupyter notebook`
4. Launch the admin_course.ipynb notebook and follow the instructions.
5. Launch the admin_assessment.ipynb notebook and follow the instructions.

### Requirements
This has been tested in Python 2.7 and 3.6 (more so in 3.6).

## Notes

### Execution
All administration methods are contained within the `GitHubLink` class. To reduce the amount of API calls to GitHub the package needs to only be initialised once as shown below. This is handled in the Jupyter Notebooks.

``` python
from ghca.gitlink import GitHubLink
ghl = GitHubLink('config/TEST000_2018_S1.json')
```
Note that only one instance of the `GitHubLink` should be used to modify objects as objects can become desynchronised.
