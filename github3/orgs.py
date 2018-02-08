# -*- coding: utf-8 -*-
"""This module contains all of the classes related to organizations."""
from __future__ import unicode_literals

import warnings
from json import dumps

from uritemplate import URITemplate

from . import users, models

from .decorators import requires_auth
from .events import Event
from .projects import Project
from .repos import Repository, ShortRepository


class Team(models.GitHubCore):

    """The :class:`Team <Team>` object.

    Please see GitHub's `Team Documentation`_ for more information.

    .. _Team Documentation:
        http://developer.github.com/v3/orgs/teams/
    """

    # Roles available to members on a team.
    members_roles = frozenset(['member', 'maintainer', 'all'])

    def _update_attributes(self, team):
        self._api = self._get_attribute(team, 'url')

        #: This team's name.
        self.name = self._get_attribute(team, 'name')
        #: This team's slug.
        self.slug = self._get_attribute(team, 'slug')
        #: Unique ID of the team.
        self.id = self._get_attribute(team, 'id')

        #: Permission level of the group.
        self.permission = self._get_attribute(team, 'permission')

        #: Number of members in this team.
        self.members_count = self._get_attribute(team, 'members_count')

        #: Members URL Template. Expands with ``member``.
        self.members_urlt = self._class_attribute(
            team, 'members_url', URITemplate
        )

        #: Number of repos owned by this team.
        self.repos_count = self._get_attribute(team, 'repos_count')

        #: Repositories url (not a template).
        self.repositories_url = self._get_attribute(team, 'repositories_url')

    def _repr(self):
        return '<Team [{0}]>'.format(self.name)

    @requires_auth
    def add_member(self, username):
        """Add ``username`` to this team.

        :param str username: the username of the user you would like to add to
            the team.
        :returns: bool
        """
        warnings.warn(
            'This is no longer supported by the GitHub API, see '
            'https://developer.github.com/changes/2014-09-23-one-more-week'
            '-before-the-add-team-member-api-breaking-change/',
            DeprecationWarning)
        url = self._build_url('members', username, base_url=self._api)
        return self._boolean(self._put(url), 204, 404)

    @requires_auth
    def add_repository(self, repository, permission=''):
        """Add ``repository`` to this team.

        If a permission is not provided, the team's default permission
        will be assigned, by GitHub.

        :param str repository: (required), form: 'user/repo'
        :param str permission: (optional), ('pull', 'push', 'admin')
        :returns: bool
        """
        data = {}
        if permission:
            data = {'permission': permission}
        url = self._build_url('repos', repository, base_url=self._api)
        return self._boolean(self._put(url, data=dumps(data)), 204, 404)

    @requires_auth
    def delete(self):
        """Delete this team.

        :returns: bool
        """
        return self._boolean(self._delete(self._api), 204, 404)

    @requires_auth
    def edit(self, name, permission=''):
        """Edit this team.

        :param str name: (required)
        :param str permission: (optional), ('pull', 'push', 'admin')
        :returns: bool
        """
        if name:
            data = {'name': name, 'permission': permission}
            json = self._json(self._patch(self._api, data=dumps(data)), 200)
            if json:
                self._update_attributes(json)
                return True
        return False

    @requires_auth
    def has_repository(self, repository):
        """Check if this team has access to ``repository``.

        :param str repository: (required), form: 'user/repo'
        :returns: bool
        """
        url = self._build_url('repos', repository, base_url=self._api)
        return self._boolean(self._get(url), 204, 404)

    @requires_auth
    def invite(self, username):
        """Invite the user to join this team.

        This returns a dictionary like so::

            {'state': 'pending', 'url': 'https://api.github.com/teams/...'}

        :param str username: (required), user to invite to join this team.
        :returns: dictionary
        """
        url = self._build_url('memberships', username, base_url=self._api)
        return self._json(self._put(url), 200)

    @requires_auth
    def is_member(self, username):
        """Check if ``login`` is a member of this team.

        :param str username: (required), username name of the user
        :returns: bool
        """
        url = self._build_url('members', username, base_url=self._api)
        return self._boolean(self._get(url), 204, 404)

    @requires_auth
    def members(self, role=None, number=-1, etag=None):
        r"""Iterate over the members of this team.

        :param str role: (optional), filter members returned by their role
            in the team. Can be one of: ``"member"``, ``"maintainer"``,
            ``"all"``. Default: ``"all"``.
        :param int number: (optional), number of users to iterate over.
            Default: -1 iterates over all values
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`User <github3.users.User>`\ s
        """
        headers = {}
        params = {}
        if role in self.members_roles:
            params['role'] = role
            headers['Accept'] = 'application/vnd.github.ironman-preview+json'
        url = self._build_url('members', base_url=self._api)
        return self._iter(int(number), url, users.ShortUser, params=params,
                          etag=etag, headers=headers)

    @requires_auth
    def repositories(self, number=-1, etag=None):
        """Iterate over the repositories this team has access to.

        :param int number: (optional), number of repos to iterate over.
            Default: -1 iterates over all values
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Repository <github3.repos.Repository>`
            objects
        """
        headers = {'Accept': 'application/vnd.github.ironman-preview+json'}
        url = self._build_url('repos', base_url=self._api)
        return self._iter(int(number), url, ShortRepository, etag=etag,
                          headers=headers)

    @requires_auth
    def membership_for(self, username):
        """Retrieve the membership information for the user.

        :param str username: (required), name of the user
        :returns: dictionary
        """
        url = self._build_url('memberships', username, base_url=self._api)
        json = self._json(self._get(url), 200)
        return json or {}

    @requires_auth
    def remove_member(self, username):
        """Remove ``username`` from this team.

        :param str username: (required), username of the member to remove
        :returns: bool
        """
        warnings.warn(
            'This is no longer supported by the GitHub API, see '
            'https://developer.github.com/changes/2014-09-23-one-more-week'
            '-before-the-add-team-member-api-breaking-change/',
            DeprecationWarning)
        url = self._build_url('members', username, base_url=self._api)
        return self._boolean(self._delete(url), 204, 404)

    @requires_auth
    def revoke_membership(self, username):
        """Revoke this user's team membership.

        :param str username: (required), name of the team member
        :returns: bool
        """
        url = self._build_url('memberships', username, base_url=self._api)
        return self._boolean(self._delete(url), 204, 404)

    @requires_auth
    def remove_repository(self, repository):
        """Remove ``repository`` from this team.

        :param str repository: (required), form: 'user/repo'
        :returns: bool
        """
        url = self._build_url('repos', repository, base_url=self._api)
        return self._boolean(self._delete(url), 204, 404)


class _Organization(models.GitHubCore):

    """The :class:`Organization <Organization>` object.

    Please see GitHub's `Organization Documentation`_ for more information.

    .. _Organization Documentation:
        http://developer.github.com/v3/orgs/
    """

    # Filters available when listing members. Note: ``"2fa_disabled"``
    # is only available for organization owners.
    members_filters = frozenset(['2fa_disabled', 'all'])

    # Roles available to members in an organization.
    members_roles = frozenset(['all', 'admin', 'member'])

    def _update_attributes(self, org):
        #: URL of the avatar at gravatar
        self.avatar_url = org['avatar_url']

        # Set the type of object (this doens't come through API data)
        self.type = 'Organization'

        self.url = self._api = org['url']

        #: Unique ID of the account
        self.id = org['id']

        #: Name of the organization
        self.login = org['login']

        #: Public Members URL Template. Expands with ``member``
        self.public_members_urlt = URITemplate(org['public_members_url'])

        #: Various urls (not templates)
        for urltype in ('avatar_url', 'events_url', 'issues_url',
                        'repos_url'):
            setattr(self, urltype, org[urltype])

    def _repr(self):
        return '<Organization [{s.login}:{s.name}]>'.format(s=self)

    @requires_auth
    def add_member(self, username, team_id):
        """Add ``username`` to ``team`` and thereby to this organization.

        .. warning::
            This method is no longer valid. To add a member to a team, you
            must now retrieve the team directly, and use the ``invite``
            method.

        .. warning::
            This method is no longer valid. To add a member to a team, you
            must now retrieve the team directly, and use the ``invite``
            method.

        Any user that is to be added to an organization, must be added
        to a team as per the GitHub api.

        .. versionchanged:: 1.0

            The second parameter used to be ``team`` but has been changed to
            ``team_id``. This parameter is now required to be an integer to
            improve performance of this method.

        :param str username: (required), login name of the user to be added
        :param int team_id: (required), team id
        :returns: bool
        """
        warnings.warn(
            'This is no longer supported by the GitHub API, see '
            'https://developer.github.com/changes/2014-09-23-one-more-week'
            '-before-the-add-team-member-api-breaking-change/',
            DeprecationWarning)

        if int(team_id) < 0:
            return False

        url = self._build_url('teams', str(team_id), 'members', str(username))
        return self._boolean(self._put(url), 204, 404)

    @requires_auth
    def add_repository(self, repository, team_id):  # FIXME(jlk): add perms
        """Add ``repository`` to ``team``.

        .. versionchanged:: 1.0

            The second parameter used to be ``team`` but has been changed to
            ``team_id``. This parameter is now required to be an integer to
            improve performance of this method.

        :param str repository: (required), form: 'user/repo'
        :param int team_id: (required), team id
        :returns: bool
        """
        if int(team_id) < 0:
            return False

        url = self._build_url('teams', str(team_id), 'repos', str(repository))
        return self._boolean(self._put(url), 204, 404)

    @requires_auth
    def create_project(self, name, body=''):
        """Create a project for this organization.

        If the client is authenticated and a member of the organization, this
        will create a new project in the organization.

        :param str name: (required), name of the project
        :param str body: (optional), the body of the project
        """
        url = self._build_url('projects', base_url=self._api)
        data = {'name': name, 'body': body}
        json = self._json(self._post(
            url, data, headers=Project.CUSTOM_HEADERS), 201)
        return self._instance_or_null(Project, json)

    @requires_auth
    def create_repository(self, name, description='', homepage='',
                          private=False, has_issues=True, has_wiki=True,
                          team_id=0, auto_init=False, gitignore_template='',
                          license_template=''):
        """Create a repository for this organization.

        If the client is authenticated and a member of the organization, this
        will create a new repository in the organization.

        :param str name: (required), name of the repository
        :param str description: (optional)
        :param str homepage: (optional)
        :param bool private: (optional), If ``True``, create a private
            repository. API default: ``False``
        :param bool has_issues: (optional), If ``True``, enable issues for
            this repository. API default: ``True``
        :param bool has_wiki: (optional), If ``True``, enable the wiki for
            this repository. API default: ``True``
        :param int team_id: (optional), id of the team that will be granted
            access to this repository
        :param bool auto_init: (optional), auto initialize the repository.
        :param str gitignore_template: (optional), name of the template; this
            is ignored if auto_int = False.
        :param str license_template: (optional), name of the license; this
            is ignored if auto_int = False.
        :returns: :class:`Repository <github3.repos.Repository>`

        .. warning: ``name`` should be no longer than 100 characters
        """
        url = self._build_url('repos', base_url=self._api)
        data = {'name': name, 'description': description,
                'homepage': homepage, 'private': private,
                'has_issues': has_issues, 'has_wiki': has_wiki,
                'license_template': license_template, 'auto_init': auto_init,
                'gitignore_template': gitignore_template}
        if int(team_id) > 0:
            data.update({'team_id': team_id})
        json = self._json(self._post(url, data), 201)
        return self._instance_or_null(Repository, json)

    @requires_auth
    def conceal_member(self, username):
        """Conceal ``username``'s membership in this organization.

        :param str username: username of the organization member to conceal
        :returns: bool
        """
        url = self._build_url('public_members', username, base_url=self._api)
        return self._boolean(self._delete(url), 204, 404)

    @requires_auth
    def create_team(self, name, repo_names=[], privacy='secret', permission='pull'):
        """Create a new team and return it.

        This only works if the authenticated user owns this organization.

        :param str name: (required), name to be given to the team
        :param list repo_names: (optional) repositories, e.g.
            ['github/dotfiles']
        :param str pivacy: (optional), options:
            - ``secret` -- (default) Visible only to the group.
            - ``closed` -- Visible to the entire organisation.
        :param str permission: (optional), options:

            - ``pull`` -- (default) members can not push or administer
                repositories accessible by this team
            - ``push`` -- members can push and pull but not administer
                repositories accessible by this team
            - ``admin`` -- members can push, pull and administer
                repositories accessible by this team

        :returns: :class:`Team <Team>`
        """
        data = {'name': name, 'repo_names': repo_names,
                'privacy': privacy, 'permission': permission}
        url = self._build_url('teams', base_url=self._api)
        json = self._json(self._post(url, data), 201)
        return self._instance_or_null(Team, json)

    @requires_auth
    def edit(self, billing_email=None, company=None, email=None, location=None,
             name=None):
        """Edit this organization.

        :param str billing_email: (optional) Billing email address (private)
        :param str company: (optional)
        :param str email: (optional) Public email address
        :param str location: (optional)
        :param str name: (optional)
        :returns: bool
        """
        json = None
        data = {'billing_email': billing_email, 'company': company,
                'email': email, 'location': location, 'name': name}
        self._remove_none(data)

        if data:
            json = self._json(self._patch(self._api, data=dumps(data)), 200)

        if json:
            self._update_attributes(json)
            return True
        return False

    def is_member(self, username):
        """Check if the user named ``username`` is a member.

        :param str username: name of the user you'd like to check
        :returns: bool
        """
        url = self._build_url('members', username, base_url=self._api)
        return self._boolean(self._get(url), 204, 404)

    def is_public_member(self, username):
        """Check if the user named ``username`` is a public member.

        :param str username: name of the user you'd like to check
        :returns: bool
        """
        url = self._build_url('public_members', username, base_url=self._api)
        return self._boolean(self._get(url), 204, 404)

    def all_events(self, username, number=-1, etag=None):
        r"""Iterate over all org events visible to the authenticated user.

        :param str username: (required), the username of the currently
            authenticated user.
        :param int number: (optional), number of events to return. Default: -1
            iterates over all events available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Event <github3.events.Event>`\ s
        """
        url = self._build_url('users', username, 'events', 'orgs', self.login)
        return self._iter(int(number), url, Event, etag=etag)

    def events(self, number=-1, etag=None):
        r"""Iterate over public events for this org (deprecated).

        :param int number: (optional), number of events to return. Default: -1
            iterates over all events available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Event <github3.events.Event>`\ s

        Deprecated: Use ``public_events`` instead.
        """

        warnings.warn(
            'This method is deprecated. Please use ``public_events`` instead.',
            DeprecationWarning)
        return self.public_events(number, etag=etag)

    def public_events(self, number=-1, etag=None):
        r"""Iterate over public events for this org.

        :param int number: (optional), number of events to return. Default: -1
            iterates over all events available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Event <github3.events.Event>`\ s
        """
        url = self._build_url('events', base_url=self._api)
        return self._iter(int(number), url, Event, etag=etag)

    def members(self, filter=None, role=None, number=-1, etag=None):
        r"""Iterate over members of this organization.

        :param str filter: (optional), filter members returned by this method.
            Can be one of: ``"2fa_disabled"``, ``"all",``. Default: ``"all"``.
            Filtering by ``"2fa_disabled"`` is only available for organization
            owners with private repositories.
        :param str role: (optional), filter members returned by their role.
            Can be one of: ``"all"``, ``"admin"``, ``"member"``. Default:
            ``"all"``.
        :param int number: (optional), number of members to return. Default:
            -1 will return all available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`User <github3.users.User>`\ s
        """
        headers = {}
        params = {}
        if filter in self.members_filters:
            params['filter'] = filter
        if role in self.members_roles:
            params['role'] = role
            headers['Accept'] = 'application/vnd.github.ironman-preview+json'
        url = self._build_url('members', base_url=self._api)
        return self._iter(int(number), url, users.ShortUser, params=params,
                          etag=etag, headers=headers)

    def public_members(self, number=-1, etag=None):
        r"""Iterate over public members of this organization.

        :param int number: (optional), number of members to return. Default:
            -1 will return all available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`User <github3.users.User>`\ s
        """
        url = self._build_url('public_members', base_url=self._api)
        return self._iter(int(number), url, users.ShortUser, etag=etag)

    def project(self, id, etag=None):
        """Return the organization project with the given ID.

        :param int id: (required), ID number of the project
        :returns: :class:`Project <github3.projects.Project>` if successful,
            otherwise None
        """
        url = self._build_url('projects', id, base_url=self._github_url)
        json = self._json(self._get(url, headers=Project.CUSTOM_HEADERS), 200)
        return self._instance_or_null(Project, json)

    def projects(self, number=-1, etag=None):
        """Iterate over projects for this organization.

        :param int number: (optional), number of members to return. Default:
            -1 will return all available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Project <github3.projects.Project>`
        """
        url = self._build_url('projects', base_url=self._api)
        return self._iter(
            int(number),
            url,
            Project,
            etag=etag,
            headers=Project.CUSTOM_HEADERS
        )

    def repositories(self, type='', number=-1, etag=None):
        r"""Iterate over repos for this organization.

        :param str type: (optional), accepted values:
            ('all', 'public', 'member', 'private', 'forks', 'sources'), API
            default: 'all'
        :param int number: (optional), number of members to return. Default:
            -1 will return all available.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Repository <github3.repos.Repository>`
        """
        url = self._build_url('repos', base_url=self._api)
        params = {}
        if type in ('all', 'public', 'member', 'private', 'forks', 'sources'):
            params['type'] = type
        return self._iter(int(number), url, ShortRepository, params, etag)

    @requires_auth
    def teams(self, number=-1, etag=None):
        r"""Iterate over teams that are part of this organization.

        :param int number: (optional), number of teams to return. Default: -1
            returns all available teams.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Team <Team>`\ s
        """
        url = self._build_url('teams', base_url=self._api)
        return self._iter(int(number), url, Team, etag=etag)

    @requires_auth
    def publicize_member(self, username):
        """Make ``username``'s membership in this organization public.

        :param str username: the name of the user whose membership you wish to
            publicize
        :returns: bool
        """
        url = self._build_url('public_members', username, base_url=self._api)
        return self._boolean(self._put(url), 204, 404)

    @requires_auth
    def remove_member(self, username):
        """Remove the user named ``username`` from this organization.

        :param str username: name of the user to remove from the org
        :returns: bool
        """
        url = self._build_url('members', username, base_url=self._api)
        return self._boolean(self._delete(url), 204, 404)

    @requires_auth
    def remove_repository(self, repository, team_id):
        """Remove ``repository`` from the team with ``team_id``.

        :param str repository: (required), form: 'user/repo'
        :param int team_id: (required)
        :returns: bool
        """
        if int(team_id) > 0:
            url = self._build_url('teams', str(team_id), 'repos',
                                  str(repository))
            return self._boolean(self._delete(url), 204, 404)
        return False

    @requires_auth
    def team(self, team_id):
        """Return the team specified by ``team_id``.

        :param int team_id: (required), unique id for the team
        :returns: :class:`Team <Team>`
        """
        json = None
        if int(team_id) > 0:
            url = self._build_url('teams', str(team_id))
            json = self._json(self._get(url), 200)
        return self._instance_or_null(Team, json)


class ShortOrganization(_Organization):
    """Object for the shortened representation of an Organization.

    GitHub's API returns different amounts of information about orgs based
    upon how that information is retrieved. Often times, when iterating over
    several orgs, GitHub will return less information. To provide a clear
    distinction between the types of orgs, github3.py uses different classes
    with different sets of attributes.

    .. versionadded:: 1.0.0
    """

    pass


class Organization(_Organization):
    """Object for the full representation of a Organization.

    GitHub's API returns different amounts of information about orgs based
    upon how that information is retrieved. This object exists to represent
    the full amount of information returned for a specific org. For example,
    you would receive this class when calling
    :meth:`~github3.github.GitHub.organization`. To provide a clear
    distinction between the types of orgs, github3.py uses different classes
    with different sets of attributes.

    .. versionchanged:: 1.0.0
    """

    def _update_attributes(self, org):
        super(Organization, self)._update_attributes(org)

        # this may be blank if the org hasn't set it
        #: URL of the blog
        self.blog = self._get_attribute(org, 'blog')

        #: Name of the company
        self.company = self._get_attribute(org, 'company')

        #: datetime object representing the date the account was created
        self.created_at = org['created_at']

        #: E-mail address of the org
        self.email = self._get_attribute(org, 'email')

        # The number of people following this org
        #: Number of followers
        self.followers_count = org['followers']

        # The number of people this org follows
        #: Number of people the org is following
        self.following_count = org['following']

        #: Location of the org
        self.location = self._get_attribute(org, 'location')

        #: Display name of the org
        self.name = self._get_attribute(org, 'name')

        # The number of public_repos
        #: Number of public repos owned by the org
        self.public_repos_count = org['public_repos']

        # e.g. https://github.com/self._login
        #: URL of the org's profile
        self.html_url = org['html_url']


class Membership(models.GitHubCore):

    """The wrapper for information about Team and Organization memberships."""

    def _repr(self):
        return '<Membership [{0}]>'.format(self.organization)

    def _update_attributes(self, membership):
        self._api = self._get_attribute(membership, 'url')

        self.organization = self._class_attribute(
            membership, 'organization', ShortOrganization, self
        )

        self.organization_url = self._get_attribute(
            membership, 'organization_url'
        )

        self.state = self._get_attribute(membership, 'state')
        self.active = self.state
        if self.active:
            self.active = self.state.lower() == 'active'
        self.pending = self.state
        if self.pending:
            self.pending = self.state.lower() == 'pending'

    @requires_auth
    def edit(self, state):
        """Edit the user's membership.

        :param str state: (required), the state the membership should be in.
            Only accepts ``"active"``.
        :returns: whether the edit was successful or not
        :rtype: bool
        """
        if state and state.lower() == 'active':
            data = dumps({'state': state.lower()})
            json = self._json(self._patch(self._api, data=data), 200)
            self._update_attributes(json)
            return True
        return False
