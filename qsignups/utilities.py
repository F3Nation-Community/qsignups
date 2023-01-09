def safe_get(data, *keys):
  try:
    result = data
    for k in keys:
      if result.get(k):
        result = result[k]
      else:
        return None
    return result
  except KeyError:
    return None

def list_to_dict(l, fn):
  result = {}
  for i in (l or []):
    key = fn(i)
    if not result.get(key): result[key] = []
    result[key].append(i)
  return result

def get_user_name(array_of_user_ids, logger, client) -> str:
    names = []
    for user_id in array_of_user_ids:
        user_info_dict = client.users_info(user=user_id)
        user_name = safe_get(user_info_dict, 'user', 'profile', 'display_name') or \
                    safe_get(user_info_dict, 'user', 'profile', 'real_name') or None
        if user_name:
            names.append(user_name)
        logger.info('user_name is {}'.format(user_name))
    logger.info('names are {}'.format(names))
    if names:
        return names[0]
    else:
        return None
