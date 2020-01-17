#!/usr/bin/env python3
import sys
from json import dumps
import requests
import os
import shutil
from getpass import getpass
import subprocess
from multiprocessing import Pool
import itertools

def retry(error, tries):
    def decorator(func):
        def decorated(*args, **kwargs):
            for i in range(tries):
                try:
                    return func(*args, **kwargs)
                except error as e:
                    print(e)
        return decorated
    return decorator

class Repo:
    def __init__(self, prefix, user, password):
        self.prefix = prefix
        self.user = user
        self.password = password

    def _get(self, url):
        response = requests.get(url, auth=(self.user, self.password))
        if response.status_code == 401:
            raise Exception('Wrong credentials for {self.host}')
        json = response.json()
        if 'error' in json:
            raise Exception(json['error']['message'])
        return response
    
    def repos(self):
        for org, orgUrl in self.orgs():
            for path, url in self.orgRepos(orgUrl):
                yield os.path.join(self.prefix, self.host, *(path.split('/'))), url
                        

class Bitbucket(Repo):
    host = 'bitbucket.org'
    def orgs(self):
        yield (self.user, f'https://api.bitbucket.org/2.0/repositories/{self.user}?role=contributor')
        url = 'https://api.bitbucket.org/2.0/teams?role=member'
        while url:
            json = self._get(url).json()
            url = json.get('next')
            for item in json['values']:
                yield item['username'], item['links']['repositories']['href']

    def orgRepos(self, url):
        while url:
            json = self._get(url).json()
            url = json.get('next')
            for item in json['values']:
                yield (
                        item['full_name'],
                        next(filter(lambda i: i['name'] == 'ssh', item['links']['clone']))['href']
                        )

class Github(Repo):
    host = 'github.com'
    def orgs(self):
        yield (self.user, f'https://api.github.com/user/repos?affiliation=owner')
        url = 'https://api.github.com/user/orgs'
        while url:
            response = self._get(url)
            url = response.links.get('next', {}).get('url')
            for item in response.json():
                yield item['login'], item['repos_url']

    def orgRepos(self, url):
        while url:
            response = self._get(url)
            url = response.links.get('next', {}).get('url')
            for item in response.json():
                yield item['full_name'], item['ssh_url']

@retry(subprocess.CalledProcessError, 3)
def cloneRepo(path, url):
    # make the parent dir
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    kwargs = {'stdout':subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.path.isdir(os.path.join(path, '.git')):
        print(f'Fetching {url} to {path}')
        # fetch
        subprocess.run(['git', 'fetch'], cwd=path, check=True, **kwargs)
        # fast forward the local branch, accepting failure
        subprocess.run(['git', 'merge', '--ff-only'], cwd=path, check=False, **kwargs)
    else:
        print(f'Cloning {url} to {path}')
        # empty the dir
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path)
        # clone
        subprocess.run(['git', 'clone', url, path], check=True, **kwargs)

def cloneRepoWrapper(args):
    '''
    gross, but this way we can use something lazier than starmap
    '''
    return cloneRepo(*args)

def interleave(*iterables):
    '''
    like itertools.chain, but alternates between each iterator, removing each iterator from the set when it's done
    '''
    i = list(iterables)
    while len(i):
        for iterable in i.copy():
            try:
                yield iterable.__next__()
            except StopIteration:
                i.remove(iterable)

def consumeIterable(iterable):
    '''
    Iterate over a given iterable, discarding the results.
    '''
    for i in iterable:
        pass

if __name__ == '__main__':
    path = sys.argv[1]
    bitbucket = Bitbucket(
            path,
            os.getenv('BITBUCKET_USER') or input('Bitbucket Username: '),
            os.getenv('BITBUCKET_PASS') or getpass('Bitbucket App Password: ')
            )
    github = Github(
            path,
            os.getenv('GITHUB_USER') or input('Github Username: '),
            os.getenv('GITHUB_PASS') or getpass('Github Password: ')
            )
    with Pool(4) as p:
        # interleave in order to roughly balance the load between git hosts, and to build up the directories earlier on
        consumeIterable(p.imap_unordered(cloneRepoWrapper, interleave(bitbucket.repos(), github.repos())))
