import argparse, os, json, yaml

parser = argparse.ArgumentParser(description='Generate Slack Q Signup files')
parser.add_argument('--hostname', '-n', help='Hostname for the Slack Services', required = True)
parser.add_argument('--environment', '-e', choices=["windows", "unix"], default="unix", help='Windows or Unix - used for formatting environment')
parser.add_argument('--env_file', '-f',help='Optional file of override env variables')

def format_environment(key, value, env):
  if env == "windows":
    return f"[SetItem]"
  else:
    return f"export {key}={value or ''}"

if __name__ == "__main__":
  args = parser.parse_args()

  outfolder = "generate"
  if not os.path.exists(outfolder):
    os.mkdir(outfolder)

  manifest_file = "manifest.yaml"

  manifest = None
  with open(manifest_file, "r") as stream:
    manifest = stream.readlines()

  output_manifest = f"{outfolder}/{manifest_file}"
  with open(output_manifest, "w") as stream:
    for l in manifest:
      stream.write(l.replace("__HOSTNAME__", args.hostname))

  with open("environment.json", "r") as stream:
    environment = json.loads(stream.read())

  manifest_yaml = yaml.safe_load("\n".join(manifest))
  environment["SLACK_SCOPES"] = ','.join(manifest_yaml['oauth_config']['scopes']['bot'])

  if args.env_file and os.path.exists(args.env_file):
    with open(args.env_file, "r") as stream:
      override_env = json.loads(stream.read())

      for k,v in override_env.items():
        environment[k] = v

  env_lines = [ format_environment(k,v,args.environment) for (k,v) in environment.items()]

  output_environment = f"{outfolder}/setup"
  with open(output_environment, "w") as stream:
    stream.writelines('\n'.join(env_lines))
    stream.write('\n')

  print(f"Manifest: {output_manifest}")
  print(f"Environment: {output_environment}")
