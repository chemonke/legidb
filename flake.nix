{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          flask
          sqlalchemy
          pymysql
        ]);

        mariadb = pkgs.mariadb;

        dbStart = pkgs.writeShellApplication {
          name = "db-start";
          runtimeInputs = [ mariadb pkgs.coreutils ];
          text = ''
            exec ${./scripts/start_ephemeral_mariadb.sh} "$@"
          '';
        };

        dbStop = pkgs.writeShellApplication {
          name = "db-stop";
          runtimeInputs = [ mariadb pkgs.coreutils ];
          text = ''
            exec ${./scripts/stop_ephemeral_mariadb.sh} "$@"
          '';
        };

        runApp = pkgs.writeShellApplication {
          name = "app";
          runtimeInputs = [ pythonEnv ];
          text = ''
            export PYTHONPATH=${./.}
            export DATABASE_URL=''${DATABASE_URL:-mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb}
            echo "Starting Flask app with DATABASE_URL=$DATABASE_URL"
            exec python ${./run.py}
          '';
        };
      in {
        packages = {
          "db-start" = dbStart;
          "db-stop" = dbStop;
          app = runApp;
        };

        apps = {
          "db-start" = {
            type = "app";
            program = "${dbStart}/bin/db-start";
          };
          "db-stop" = {
            type = "app";
            program = "${dbStop}/bin/db-stop";
          };
          app = {
            type = "app";
            program = "${runApp}/bin/app";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            mariadb
          ];

          shellHook = ''
            export DATABASE_URL=''${DATABASE_URL:-mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb}
            echo "DATABASE_URL=$DATABASE_URL"
            echo "Use 'nix run .#db-start' (or scripts/start_ephemeral_mariadb.sh) to boot an ephemeral MariaDB."
          '';
        };

        formatter = pkgs.nixpkgs-fmt;
      });
}
