{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [ pkgs.poetry ];
  shellHook = ''
    poetry install
    source $(poetry env info --path)/bin/activate
  '';
}
