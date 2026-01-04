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
          flask-admin
          sqlalchemy
          pymysql
          markdown
        ]);

        mariadb = pkgs.mariadb;

        dbStart = pkgs.writeShellApplication {
          name = "db-start";
          runtimeInputs = [ mariadb pkgs.coreutils ];
          text = ''
            # Substitute store paths for schema/sample when running remotely.
            LEGIDB_SCHEMA_SQL="${./data/schema.sql}" \
            LEGIDB_SAMPLE_SQL="${./data/sample_data.sql}" \
            exec "${./scripts/start_ephemeral_mariadb.sh}" "$@"
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
            # Prefer live working tree (for new templates/static files), fallback to store copy.
            export PYTHONPATH="$PWD:${./.}"
            export DATABASE_URL=''${DATABASE_URL:-mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb}
            echo "Starting Flask app with DATABASE_URL=$DATABASE_URL"
            exec python ${./run.py}
          '';
        };

        dockerDevImage = pkgs.dockerTools.buildLayeredImage {
          name = "legidb-dev";
          tag = "latest";
          # Include the same toolchain as the dev shell so non-Nix users can work from a container.
          contents = [
            (pkgs.buildEnv {
              name = "legidb-dev-env";
              paths = [
                pythonEnv
                mariadb
                pkgs.nix
                pkgs.coreutils
                pkgs.git
                pkgs.bashInteractive
                pkgs.findutils
                pkgs.gnugrep
                pkgs.gnused
                pkgs.procps
                pkgs.cacert
              ];
              pathsToLink = [ "/bin" "/etc" "/lib" "/share" ];
            })
          ];
          config = {
            User = "1000:1000";
            Env = [
              "DATABASE_URL=mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb"
              "PATH=/bin:/usr/bin:/usr/local/bin"
              "LC_ALL=C.UTF-8"
              "HOME=/workspace"
              "NIX_SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
              "NIX_CONFIG=experimental-features = nix-command flakes\nbuild-users-group ="
            ];
            WorkingDir = "/workspace";
            Volumes = { "/workspace" = {}; };
            Cmd = [ "bash" ];
          };
        };
      in {
        packages = {
          "db-start" = dbStart;
          "db-stop" = dbStop;
          app = runApp;
          docker-image-dev = dockerDevImage;
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
