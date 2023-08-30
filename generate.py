import argparse, os, json, yaml, shutil

parser = argparse.ArgumentParser(description='Generate Slack Q Signup files')
parser.add_argument('--hostname', '-n', help='Hostname for the Slack Services', required = True)
parser.add_argument('--env', '-e', choices=["prod", "dev"], default="dev", help='prod or dev build')
parser.add_argument('--os', '-o', choices=["windows", "unix"], default="unix", help='Windows or Unix - used for formatting environment')
parser.add_argument('--env_file', '-f',help='Optional file of override env variables')
parser.add_argument('--aws_key', '-k', help='AWS Access Key')
parser.add_argument('--aws_secret', '-s', help='AWS Secret')
parser.add_argument('--qlambda_name', '-l', help='Deployment lambda name')
parser.add_argument('--generate', '-g', choices=["environment", "manifest", "config", "all"], default="all", help='What to generate')
parser.add_argument('--clean', '-c', action="store_true")

def enviromnet_file(os):
  if os == "windows":
    return "setup.ps1"
  else:
    return "setup"

def format_environment(key, value, os):
  if os == "windows":
    return f'$env:{key}="{value}"'
  else:
    return f'export {key}={value or ""}'

def load_environment(env, user_env_file):
  with open("environment.json", "r") as stream:
    environment = json.loads(stream.read())

  if environment.get(env):
    env_overrides = environment.pop(env)
    environment = {
      **environment,
      **env_overrides
    }

  keys_to_pop = []
  for k in environment.keys():
    if k.islower():
      keys_to_pop += [k]
  for k in keys_to_pop:
    environment.pop(k)

  if user_env_file and os.path.exists(user_env_file):
    with open(user_env_file, "r") as stream:
      override_env = json.loads(stream.read())

      for k,v in override_env.items():
        environment[k] = v

  return environment

def generate_manifest(outfolder, hostname):
  manifest_file = "manifest.yaml"
  with open(manifest_file, "r") as stream:
    manifest_lines = stream.readlines()

  output_manifest = f"{outfolder}/{manifest_file}"
  with open(output_manifest, "w") as stream:
    for l in manifest_lines:
      stream.write(l.replace("__HOSTNAME__", hostname))
  return output_manifest

def generate_environment(outfolder, env, user_env_file, op_system):
  environment = load_environment(env, user_env_file)
  manifest_file = "manifest.yaml"
  with open(manifest_file, "r") as stream:
    manifest_lines = stream.readlines()
    manifest_yaml = yaml.safe_load("\n".join(manifest_lines))

  environment["SLACK_SCOPES"] = ','.join(manifest_yaml['oauth_config']['scopes']['bot'])
  env_lines = [ format_environment(k,v,op_system) for (k,v) in environment.items()]

  output_environment = f"{outfolder}/{enviromnet_file(op_system)}"
  with open(output_environment, "w") as stream:
    stream.writelines('\n'.join(env_lines))
    stream.write('\n')
  return output_environment

def replace(s, key, val):
  return s.replace(f"__{key.upper()}__", (os.environ.get(key.upper()) or val or ""))

def generate_aws_config(outfolder, **kwargs):
  input_aws_config = "aws_config_template.yaml"
  with open(input_aws_config, "r") as stream:
    config_lines = stream.readlines()

  output_aws_config = f"{outfolder}/aws_config.yaml"
  with open(output_aws_config, "w") as stream:
    for l in config_lines:
      for k,v in kwargs.items():
        l = replace(l, k, v)
      stream.write(l)
  return output_aws_config

if __name__ == "__main__":
  args = parser.parse_args()

  outfolder = "generate"
  if args.clean:
    if os.path.exists(outfolder):
      shutil.rmtree(outfolder)

  if not os.path.exists(outfolder):
    os.mkdir(outfolder)

  if args.generate == "all" or args.generate == "manifest":
    manifest_file = generate_manifest(outfolder, args.hostname)
    print(f"Manifest: {manifest_file}")

  if args.generate == "all" or args.generate == "config":
    aws_config_file = generate_aws_config(
      outfolder,
      aws_key = args.aws_key,
      aws_secret = args.aws_secret,
      qlambda_name = args.qlambda_name)
    print(f"AWS Config: {aws_config_file}")

  if args.generate == "all" or args.generate == "environment":
    environment_file = generate_environment(outfolder, args.env, args.env_file, args.os)
    print(f"Environment: {environment_file}")
