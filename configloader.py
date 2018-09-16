import yaml
import logging


def get_config_from_file(file='config/config.yaml'):
    data = None
    try:
        with open(file, 'r') as config_fp:
            data = yaml.load(config_fp)
    except PermissionError:
        logging.critical("Permission error while trying to load configuration file {}".format(file))
        return False
    except FileNotFoundError:
        logging.critical("Configuration file «{}» not found".format(file))
        return False
    except yaml.parser.ParserError:
        logging.critical("Configuration file «{}» has no yaml format".format(file))
        return False
    finally:
        if data:
            return data
