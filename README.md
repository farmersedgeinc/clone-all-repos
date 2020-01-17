# clone-all-repos

Clone all the bitbucket and github repos for all the orgs you belong to.

## requirements

- python 3.7
- requests module
- git

## usage

```
./clone-all-repos.py <parent_dir>
```

The script will prompt you for bitbucket and github credentials. The username must be your actual username (not your email address), and the passwords both need to be "app passwords":

- https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line. Scopes:
    - read:org
    - read:user
- https://confluence.atlassian.com/bitbucket/app-passwords-828781300.html. Permissions:
    - Account/Read
    - Team membership/Read
    - Repositories/Read

If you set the environment variables `BITBUCKET_USER`, `BITBUCKET_PASS`, `GITHUB_USER`, `GITHUB_PASS`, you can skip the prompts.

## example

To save having to type your credentials in, you can write a small wrapper:

```
#! /bin/bash
export  BITBUCKET_USER=myname \
        BITBUCKET_PASS="$(mypasswordcommand)" \
        GITHUB_USER=myname \
        GITHUB_PASS="$(mypasswordcommand)"
./clone-all-repos.py ~/src
```

With `myname` replaced with your usernames, and `mypasswordcommand` replaced with a command that prints your password. For example: `pass github/username/clone-all-repos` if you use [`pass`](https://www.passwordstore.org/)
