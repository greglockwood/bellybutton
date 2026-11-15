"""Git-backed tests for modified-only lint selection."""

import subprocess

from bellybutton import cli


def git(directory, *arguments):
    subprocess.check_call(['git', '-C', str(directory)] + list(arguments))


def make_repo(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    git(source, 'init', '-b', 'master')
    git(source, 'config', 'user.name', 'Bellybutton Test')
    git(source, 'config', 'user.email', 'test@example.invalid')

    for name in ('deleted.py', 'renamed.py', 'changed.py'):
        (source / name).write_text('value = 1\n')
    (source / '.bellybutton.yml').write_text(
        'default_settings: !settings\n'
        '  included: ["*"]\n'
        '  excluded: []\n'
        '  allow_ignore: no\n'
        'rules:\n'
        '  NoPrint:\n'
        '    description: Print calls are forbidden.\n'
        '    expr: //Call[func/Name/@id="print"]\n'
    )
    git(source, 'add', '.')
    git(source, 'commit', '-m', 'Initial files')

    remote = tmp_path / 'remote.git'
    subprocess.check_call(['git', 'clone', '--bare', str(source), str(remote)])
    work = tmp_path / 'work'
    subprocess.check_call(['git', 'clone', str(remote), str(work)])
    git(work, 'config', 'user.name', 'Bellybutton Test')
    git(work, 'config', 'user.email', 'test@example.invalid')
    git(work, 'checkout', '-b', 'feature')
    return work


def test_modified_only_lints_rename_destination_and_skips_deleted_path(tmp_path, capsys):
    work = make_repo(tmp_path)
    git(work, 'rm', 'deleted.py')
    git(work, 'mv', 'renamed.py', 'new.py')
    (work / 'new.py').write_text('print("bad")\n')
    git(work, 'add', 'new.py')
    (work / 'changed.py').write_text('value = 2\n')
    git(work, 'add', 'changed.py')

    assert cli.get_git_modified(str(work)) == {
        str(work / 'new.py'), str(work / 'changed.py')
    }
    assert cli.lint(modified_only=True, project_directory=str(work)) == 1
    assert 'new.py:1\tNoPrint' in capsys.readouterr().out


def test_modified_only_includes_branch_commits_relative_to_base(tmp_path):
    work = make_repo(tmp_path)
    git(work, 'rm', 'deleted.py')
    git(work, 'mv', 'renamed.py', 'new.py')
    (work / 'new.py').write_text('print("bad")\n')
    git(work, 'add', 'new.py')
    git(work, 'commit', '-m', 'Rename and delete Python files')

    assert cli.get_git_modified(str(work)) == {str(work / 'new.py')}


def test_modified_only_keeps_git_quoted_python_names(tmp_path):
    work = make_repo(tmp_path)
    unusual_name = 'renamed\nfile.py'
    git(work, 'mv', 'renamed.py', unusual_name)

    assert cli.get_git_modified(str(work)) == {str(work / unusual_name)}
