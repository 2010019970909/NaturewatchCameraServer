"""Find the dependencies of a package from the piwheels API."""
from __future__ import annotations

import locale
import subprocess
import sysconfig

import requests


def fetch_json(package_name: str) -> dict:
    """Fetch the json file from the given package name.

    Args:
        package_name (str): The name of the package to fetch.

    Returns:
        dict: The json file from the API.
    """
    url = f'https://www.piwheels.org/project/{package_name}/json/'
    return requests.get(url, timeout=10).json()


def find_newest_compatible_wheels(
        package_name: str, python_version: str | None = None) -> str:
    """Find the newest compatible wheel files for the given package and python version.

    Args:
        package_name (str): The name of the package to fetch.
        python_version (str | None, optional): Python version as `cpxx`.
        Defaults to None (use current Python version).

    Raises:
        ValueError: if no compatible wheel file is found.

    Returns:
        tuple: The newest compatible version and its dependencies.
    """
    data = fetch_json(package_name)
    releases = data['releases']
    releases_versions = list(releases.keys())

    # Find the first release compatible with the current python version
    # which has a wheel file and find its dependencies
    if python_version is None:
        python_version = f'cp{sysconfig.get_config_var("py_version_nodot")}'

    latest_compatible_release = None
    matching_wheels = None

    for version in releases_versions:
        wheels = list(releases[version]['files'].keys())

        matching_wheels = []
        for wheel in wheels:
            if python_version in wheel:
                latest_compatible_release = version
                matching_wheels.append(wheel)

        if latest_compatible_release is not None:
            break

    if latest_compatible_release is None:
        raise ValueError(
            'No release compatible with the current python version '
            f'({python_version})')

    # Merge all dependencies in one list of unique values
    files = releases[latest_compatible_release]['files']
    merged_dependencies = []
    for matching_wheel in matching_wheels:
        merged_dependencies.extend(files[matching_wheel]['apt_dependencies'])
    merged_dependencies = list(set(merged_dependencies))

    return latest_compatible_release, merged_dependencies


def generate_apt_get_command(packages: list[str]):
    """Generate the apt-get command to install the dependencies."""
    return ['apt-get', 'install'] + packages + ['--ignore-missing', '-y']


def run_command(command_list: list):
    """ Run the command and directly output to the console. """
    process = subprocess.Popen(command_list, stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            print(output.decode(
                locale.getdefaultlocale()[1], encoding='utf-8'), end='')
    return process.poll()


if __name__ == '__main__':
    import argparse
    # Parse package name and optionaly the python version
    parser = argparse.ArgumentParser(
        description='Find the dependencies of a package '
        'from the piwheels API. The script will look for'
        ' the latest compatible wheel available for the '
        'specified or current python version.'
    )
    parser.add_argument('package_name', type=str,
                        help='The name of the package to fetch.')
    parser.add_argument('--python-version', type=str, default=None,
                        help='Python version as `cpxx`.')
    args = parser.parse_args()

    release, dependencies = find_newest_compatible_wheels(
        args.package_name, args.python_version
    )

    command = generate_apt_get_command(dependencies)

    print(f'Installing dependencies for {release}...')
    run_command(command)
