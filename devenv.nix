{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";
  env.LD_LIBRARY_PATH = "${pkgs.libGL}/lib:${pkgs.zlib}/lib:${pkgs.glib.out}/lib:${pkgs.file}/lib";

  # https://devenv.sh/packages/
  packages = [ pkgs.git pkgs.uv pkgs.zlib pkgs.libGL pkgs.glib pkgs.file ];

  # https://devenv.sh/languages/
  languages.python.enable = true;
  languages.python.uv.enable = true;

  # https://devenv.sh/processes/
  # processes.dev.exec = "${lib.getExe pkgs.watchexec} -n -- ls -la";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  # https://devenv.sh/basics/
  enterShell = ''
    uv --version
    cd app && uv sync && cd ..
  '';

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/git-hooks/
  # git-hooks.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
