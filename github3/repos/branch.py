# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import dumps

from ..decorators import requires_auth
from ..models import GitHubCore

from .commit import RepoCommit


class Branch(GitHubCore):
    """The :class:`Branch <Branch>` object. It holds the information GitHub
    returns about a branch on a
    :class:`Repository <github3.repos.repo.Repository>`.
    """

    # The Accept header will likely be removable once the feature is out of
    # preview mode. See: http://git.io/v4O1e
    PREVIEW_HEADERS = {'Accept': 'application/vnd.github.loki-preview+json'}

    def _update_attributes(self, branch):
        #: Name of the branch.
        self.name = self._get_attribute(branch, 'name')

        #: Returns the branch's
        #: :class:`RepoCommit <github3.repos.commit.RepoCommit>` or ``None``.
        self.commit = self._class_attribute(branch, 'commit', RepoCommit, self)

        #: Returns '_links' attribute.
        self.links = self._get_attribute(branch, '_links', [])

        if self.links and 'self' in self.links:
            self._api = self.links['self']
        elif isinstance(self.commit, RepoCommit):
            # Branches obtained via `repo.branches` don't have links.
            base = self.commit.url.split('/commit', 1)[0]
            self._api = self._build_url('branches', self.name, base_url=base)

        #: Provides the branch's protection attributes.
        self.protected = self._get_attribute(branch, 'protected')

        self.protection_url = self._get_attribute(branch, 'protection_url')

    def _repr(self):
        return '<Repository Branch [{0}]>'.format(self.name)

    def latest_sha(self, differs_from=''):
        """Check if SHA-1 is the same as remote branch

        See: https://git.io/vaqIw

        :param str differs_from: (optional), sha to compare against
        :returns: string of the SHA or None
        """
        # If-None-Match returns 200 instead of 304 value does not have quotes
        headers = {
            'Accept': 'application/vnd.github.chitauri-preview+sha',
            'If-None-Match': '"{0}"'.format(differs_from)
        }
        base = self._api.split('/branches', 1)[0]
        url = self._build_url('commits', self.name, base_url=base)
        resp = self._get(url, headers=headers)
        if self._boolean(resp, 200, 304):
            return resp.content
        return None

    def protection(self):
        """Get the Branch's :class:`Protection <github3.repos.branch.Protection>`
        object.
        """
        json = self._json(self._get(self.protection_url,
                                    headers=Branch.PREVIEW_HEADERS), 200)
        return self._instance_or_null(Protection, json)

    @requires_auth
    def protect(self, required_status_checks=None, restrictions=None,
                required_pull_request_reviews=None, enforce_admins=False):
        """Update this :class:`Protection <github3.repos.branch.Protection>`
        object.

        https://developer.github.com/v3/repos/branches/#update-branch-protection

        :param dict required_status_checks: (required) Supports include_admins,
            strict and contexts keys.
        :param dict restrictions: (required) Restrict permission to users and
            or teams. Supports users and teams keys.
        :param dict required_pull_request_reviews: (optional) Supports
            include_admins key.
        :param dict enforce_admins: (optional) The enforce_admins object is a
            boolean value: setting it to true enforces required status checks
            for repository administrators.

        :returns: bool
        """
        edit = {'required_status_checks': required_status_checks,
                'required_pull_request_reviews': required_pull_request_reviews,
                'enforce_admins': enforce_admins, 'restrictions': restrictions}
        json = self._json(self._put(self.protection_url, data=dumps(edit),
                                    headers=self.PREVIEW_HEADERS), 200)
        if json:
            self.protected = True
            return True

    @requires_auth
    def unprotect(self):
        """Disable force push protection on this branch."""
        result = self._boolean(self._delete(self.protection._api,
                                            headers=self.PREVIEW_HEADERS),
                               204, 404)
        if result:
            self.protected = False
        return result


class Protection(GitHubCore):
    """The :class:`Protection <Protection>` object.

    It holds information GitHub returns about protected
    :class:`Branch <github3.repos.repo.Branch>`.
    """

    # The Accept header will likely be removable once the feature is out of
    # preview mode. See: http://git.io/v4O1e
    PREVIEW_HEADERS = {'Accept': 'application/vnd.github.loki-preview+json'}

    def _update_attributes(self, protection):
        self.url = self._get_attribute(protection, 'url')
        self._api = self.url

        self.required_status_checks = self._class_attribute(
            protection,
            'required_status_checks', RequiredStatusChecks, self)

        self.required_pull_request_reviews = self._class_attribute(
            protection, 'required_pull_request_reviews',
            RequiredPullRequestReviews, self)

        self.enforce_admins = self._class_attribute(
            protection, 'enforce_admins', EnforceAdmins, self)

        self.restrictions = self._class_attribute(
            protection, 'restrictions', Restrictions, self)

        self.branch_name = self._api.split(
            'repos/', 1)[1].split('/branches', 1)[0]

    def _repr(self):
        return '<Protection [{0}]>'.format(self.branch_name)

    def get_required_status_checks(self):
        """Retrieve the :class:`RequiredStatusChecks
        <github3.repos.branch.RequiredStatusChecks>` for the branch.
        """
        url = self._build_url('required_status_checks', base_url=self._api)
        json = self._json(self._get(url,
                                    headers=Branch.PREVIEW_HEADERS), 200)
        return self._instance_or_null(RequiredStatusChecks, json)

    def get_required_pull_request_reviews(self):
        """Retrieve the :class:`RequiredPullRequestReviews
        <github3.repos.branch.RequiredPullRequestReviews>` for the branch.
        """
        url = self._build_url('required_pull_request_reviews',
                              base_url=self._api)
        json = self._json(self._get(url,
                                    headers=Branch.PREVIEW_HEADERS), 200)
        return self._instance_or_null(RequiredPullRequestReviews, json)

    def get_enforce_admins(self):
        """Retrieve the :class:`EnforceAdmins <github3.repos.branch.EnforceAdmins>`
        for the branch.
        """
        url = self._build_url('enforce_admins', base_url=self._api)
        json = self._json(self._get(url,
                                    headers=Branch.PREVIEW_HEADERS), 200)
        return self._instance_or_null(EnforceAdmins, json)

    def get_restrictions(self):
        """Retrieve the :class:`Restrictions <github3.repos.branch.Restrictions>`
        for the branch.
        """
        url = self._build_url('restrictions', base_url=self._api)
        json = self._json(self._get(url,
                                    headers=Branch.PREVIEW_HEADERS), 200)
        return self._instance_or_null(Restrictions, json)

    @requires_auth
    def update(self, required_status_checks=None, restrictions=None,
               required_pull_request_reviews=None, enforce_admins=False):
        """Update this :class:`Protection <github3.repos.branch.Protection>`
        object.

        https://developer.github.com/v3/repos/branches/#update-branch-protection

        :param dict required_status_checks: (required) Supports include_admins,
            strict and contexts keys.
        :param dict restrictions: (required) Restrict permission to users and
            or teams. Supports users and teams keys.
        :param dict required_pull_request_reviews: (optional) Supports
            include_admins key.
        :param dict enforce_admins: (optional) The enforce_admins object is a
            boolean value: setting it to true enforces required status checks
            for repository administrators.

        :returns: bool
        """
        edit = {'required_status_checks': required_status_checks,
                'required_pull_request_reviews': required_pull_request_reviews,
                'enforce_admins': enforce_admins, 'restrictions': restrictions}
        json = self._json(self._put(self._api, data=dumps(edit),
                                    headers=self.PREVIEW_HEADERS), 200)
        self._update_attributes(json)
        return True

    @requires_auth
    def delete(self):
        """Disable force push protection on this branch."""
        return self._boolean(
            self._delete(self._api, headers=Protection.PREVIEW_HEADERS),
            204, 404)


class RequiredStatusChecks(GitHubCore):
    """The :class:`RequiredStatusChecks
    <github3.repos.branch.RequiredStatusChecks>` object.

    This allows status checks to protect the branch.

    The `strict` attribute ensures the branch is rebased.
    """

    def _update_attributes(self, status_checks):
        self.url = self._get_attribute(status_checks, 'url')
        self._api = self.url

        self.include_admins = self._get_attribute(status_checks,
                                                  'include_admins')

        self.strict = self._get_attribute(status_checks, 'strict')

        self.contexts_url = self._get_attribute(status_checks, 'contexts_url')
        self.contexts = self._iter(-1, self.contexts_url, str,
                                   headers=Protection.PREVIEW_HEADERS)

        self.branch_name = self._api.split(
            'repos/', 1)[1].split('/branches', 1)[0]

    def _repr(self):
        return '<Required Status Checks [{0}]>'.format(self.branch_name)

    @requires_auth
    def delete(self):
        """Remove required status checks."""
        return self._boolean(
            self._delete(self._api,
                         headers=Protection.PREVIEW_HEADERS), 204, 404)

    @requires_auth
    def update(self, include_admins=None, strict=None, contexts=None):
        """Update the :class:`RequiredStatusChecks
        <github3.repos.branch.RequiredStatusChecks>` object.

        :param boolean include_admins: Enforce required status checks for
            repository administrators.
        :param boolean strict: Require branches to be up to date before
            merging.
        :param list of strings contexts: The list of status checks to
            require in order to merge into this branch.

        :returns: bool
        """
        edit = {'include_admins': include_admins, 'strict': strict,
                'contexts': contexts}
        self._remove_none(edit)
        json = self._json(self._patch(self._api, data=dumps(edit),
                                      headers=Protection.PREVIEW_HEADERS), 200)
        if json:
            return True

    def list_contexts(self):
        """List required status checks contexts of protected branch."""
        return self._iter(-1, self.contexts_url, str,
                          headers=Protection.PREVIEW_HEADERS)

    @requires_auth
    def add_contexts(self, *contexts):
        """Add required status checks contexts of protected branch.

        :param str contexts: (required), Contexts you wish to add.

        :
        """
        return self._boolean(
            self._post(self.contexts_url, data=contexts,
                       headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def replace_contexts(self, *contexts):
        """Replace required status checks contexts of protected branch.

        :param str contexts: (required), Replace with these contexts.
        """
        return self._boolean(
            self._put(self.contexts_url, data=dumps(contexts),
                      headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def delete_contexts(self, *contexts):
        """Remove required status checks contexts of protected branch.

        :param str contexts: (required), Contexts you wish to delete.
        """
        return self._boolean(
            self._delete(self.contexts_url, data=dumps(contexts),
                         headers=Protection.PREVIEW_HEADERS), 200, 404)


class RequiredPullRequestReviews(GitHubCore):
    """The :class:`RequiredPullRequestReviews
    <github3.repos.branch.RequiredPullRequestReviews>` object.

    Adding this enforces pull request reviews for the branch.
    """

    def _update_attributes(self, pr_reviews):
        self.url = self._get_attribute(pr_reviews, 'url')
        self._api = self.url

        self.include_admins = self._get_attribute(pr_reviews,
                                                  'include_admins')

        self.dismissal_restrictions = self._class_attribute(
            pr_reviews, 'dismissal_restrictions',
            DismissalRestrictions, self)

        self.branch_name = self._api.split(
            'repos/', 1)[1].split('/branches', 1)[0]

    def _repr(self):
        return '<Required Pull Request Reviews [{0}]>'.format(self.branch_name)

    @requires_auth
    def delete(self):
        """Remove required pull request reviews."""
        return self._boolean(
            self._delete(self._api,
                         headers=Protection.PREVIEW_HEADERS), 204, 404)

    @requires_auth
    def update(self, include_admins=None, dismissal_restrictions=None):
        """Update the :class:`RequiredPullRequestReviews
        <github3.repos.branch.RequiredPullRequestReviews>` object.

        :param boolean include_admins: Enforce required pull request
            reviews for repository administrators.
        :param dict dismissal_restrictions: Specify which users and
            teams can dismiss pull request reviews. A dictionary with
            a list of user logins and list of team slugs.
        :returns: bool
        """
        edit = {'include_admins': include_admins,
                'dismissal_restrictions': dismissal_restrictions}
        self._remove_none(edit)
        json = self._json(self._patch(self._api, data=dumps(edit),
                                      headers=Protection.PREVIEW_HEADERS), 200)
        if json:
            return True


class EnforceAdmins(GitHubCore):
    """The :class:`EnforceAdmins <github3.repos.branch.EnforceAdmins>`
    object.

    Enforces permissions checks for repository administrators.
    """

    def _update_attributes(self, enforce_admins):
        self.url = self._get_attribute(enforce_admins, 'url')
        self._api = self.url

        self.enabled = self._get_attribute(enforce_admins,
                                           'enabled')

        self.branch_name = self._api.split(
            'repos/', 1)[1].split('/branches', 1)[0]

    def _repr(self):
        return '<Enforce Admins [{0}]>'.format(self.branch_name)

    @requires_auth
    def add(self):
        """Enforce permissions checks for repository administrators.

        Admin enforcement requires admin access and branch
        protection to be enabled.
        """
        return self._boolean(
            self._post(self._api,
                       headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def delete(self):
        """Remove enforcement of permissions checks for repository
        administrators.

        Admin enforcement requires admin access and branch
        protection to be enabled.
        """
        return self._boolean(
            self._delete(self._api,
                         headers=Protection.PREVIEW_HEADERS), 204, 404)


class Restrictions(GitHubCore):
    """The :class:`DismissalRestrictions <DismissalRestrictions>` object.

    Specify which users and teams with push access.

    Note: Passing new arrays of users and teams replaces their previous values.
    """

    def _update_attributes(self, restrictions):
        self.url = self._get_attribute(restrictions, 'url')
        self._api = self.url

        #: Partial :class:`User <github3.users.User>` representing
        #: the users with permission.
        self.users_url = self._get_attribute(restrictions, 'users_url')
        self.users = self._get_attribute(restrictions, 'users')

        #: Partial :class:`Team <github3.ogrs.Team>` representing
        #: the teams with permission.
        self.teams_url = self._get_attribute(restrictions, 'teams_url')
        self.teams = self._get_attribute(restrictions, 'teams')

        self.branch_name = self._api.split(
            'repos/', 1)[1].split('/branches', 1)[0]

    def _repr(self):
        return '<Restrictions [{0}]>'.format(self.branch_name)

    @requires_auth
    def delete(self):
        """Remove team and user restrictions."""
        return self._boolean(
            self._delete(self._api,
                         headers=Protection.PREVIEW_HEADERS), 204, 404)

    def list_users(self):
        """List user restrictions for the protected branch."""
        return self._iter(-1, self.users_url, str,
                          headers=Protection.PREVIEW_HEADERS)

    @requires_auth
    def add_users(self, *users):
        """Add user restrictions for the protected branch.

        :param str users: (required), User logins you wish to
        add.
        """
        return self._boolean(
            self._post(self.users_url, data=users,
                       headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def replace_users(self, *users):
        """Replace user restrictions for the protected branch.

        :param str users: (required), Replace with these user logins.
        """
        return self._boolean(
            self._put(self.users_url, data=dumps(users),
                      headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def delete_users(self, *users):
        """Remove user restrictions for the protected branch.

        :param str users: (required), User logins you wish to
        delete.
        """
        return self._boolean(
            self._delete(self.users_url, data=dumps(users),
                         headers=Protection.PREVIEW_HEADERS), 200, 404)

    def list_teams(self):
        """List team restrictions for the protected branch."""
        return self._iter(-1, self.teams_url, str,
                          headers=Protection.PREVIEW_HEADERS)

    @requires_auth
    def add_teams(self, *teams):
        """Add team restrictions for the protected branch.

        :param str teams: (required), Team slugs you wish to
        add.
        """
        return self._boolean(
            self._post(self.teams_url, data=teams,
                       headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def replace_teams(self, *teams):
        """Replace team restrictions for the protected branch.

        :param str teams: (required), Replace with these team slugs.
        """
        return self._boolean(
            self._put(self.teams_url, data=dumps(teams),
                      headers=Protection.PREVIEW_HEADERS), 200, 404)

    @requires_auth
    def delete_teams(self, *teams):
        """Remove team restrictions of the protected branch.

        :param str teams: (required), Team slugs you wish to
        delete.
        """
        return self._boolean(
            self._delete(self.teams_url, data=dumps(teams),
                         headers=Protection.PREVIEW_HEADERS), 200, 404)


class DismissalRestrictions(Restrictions):
    """The :class:`DismissalRestrictions <DismissalRestrictions>` object.

    Specify which users and teams can dismiss pull request reviews.

    Note: Passing new arrays of users and teams replaces their previous values.
    """

    def _repr(self):
        return '<Dismissal Restrictions [{0}]>'.format(self.branch_name)
