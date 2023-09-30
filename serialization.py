import yaml


def serialize_config(config_data):
    try:
        config_str = yaml.dump(config_data, default_flow_style=False)
        return config_str
    except Exception as e:
        print(f"Error serializing config: {str(e)}")
        return None


def deserialize_config(config_str):
    print(config_str)
    try:
        config_data = yaml.safe_load(config_str)
        return config_data
    except Exception as e:
        print(f"Error deserializing config: {str(e)}")
        return None
