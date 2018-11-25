import argparse
from data_loader import load_debug, load_dummy_fixed_length, load_dummy_variable_length, load_iwslt
import json
from model import Encoder, Decoder
import os
import torch.nn as nn
import torch.optim as optim
from utils import get_or_create_dir


def get_config(use_gpu, device, device_idx):
    args = parse_arguments()
    config_path = args.config
    with open(config_path, 'r') as f:
        config = json.load(f)
    EOS_token = '<EOS>'
    SOS_token = '<SOS>'
    if args.debug:
        train_iter, val_iter, src_language, trg_language, _, val_dataset = load_debug(config, SOS_token, EOS_token, device)
    elif args.dummy_fixed_length:
        train_iter, val_iter, src_language, trg_language, _, val_dataset = load_dummy_fixed_length(config, SOS_token, EOS_token, device)
    elif args.dummy_variable_length:
        train_iter, val_iter, src_language, trg_language, _, val_dataset = load_dummy_variable_length(config, SOS_token, EOS_token, device)
    else:
        train_iter, val_iter, src_language, trg_language, _, val_dataset = load_iwslt(config, SOS_token, EOS_token, device)
    if args.name is not None:
        config['name'] = args.name
    file_path = os.path.dirname(os.path.realpath(__file__))
    config['writer_path'] = get_or_create_dir(file_path, f'.logs/{config.get("name")}')
    config['EOS_token'] = EOS_token
    config['SOS_token'] = EOS_token
    config['source_vocabulary_size'] = len(src_language.itos)
    config['target_vocabulary_size'] = len(trg_language.itos)
    config['train_iter'] = train_iter
    config['val_iter'] = val_iter
    config['src_language'] = src_language
    config['trg_language'] = trg_language
    config['val_dataset'] = val_dataset
    config["decoder"] = Decoder(config, device)
    config["encoder"] = Encoder(config, device)
    if use_gpu:
        config["decoder"] = config["decoder"].to(device)
        config["encoder"] = config["encoder"].to(device)
    config['encoder_optimizer'] = get_optimizer(config.get('optimizer'), config['encoder'])
    config['decoder_optimizer'] = get_optimizer(config.get('optimizer'), config['decoder'])
    config['loss_fn'] = get_loss_fn(config)
    return config


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def parse_arguments():
    dummy_fixed_length_help = 'Dummy data with fixed length.'
    dummy_variable_length_help = 'Dummy data with variable length.'
    parser = argparse.ArgumentParser(description='Train machine translation model.')
    parser.add_argument('--config', type=str, nargs='?', default='configs/default.json', help='Path to model configuration.')
    parser.add_argument('--debug', type=str2bool, default=False, const=True, nargs='?', help='Debug mode.')
    parser.add_argument('--dummy_fixed_length', type=str2bool, default=False, const=True, nargs='?', help=dummy_fixed_length_help)
    parser.add_argument('--dummy_variable_length', type=str2bool, default=False, const=True, nargs='?', help=dummy_variable_length_help)
    parser.add_argument('--name', default=None, type=str, help='Name used when writing to tensorboard.')
    return parser.parse_args()


def get_loss_fn(config):
    loss_fn = config.get('loss_fn')
    if loss_fn == 'CrossEntropyLoss':
        return nn.CrossEntropyLoss()
    elif loss_fn == 'NLLLoss':
        return nn.NLLLoss()
    else:
        raise Exception(f'Unknown loss function: {loss_fn}')


def get_optimizer(config, model):
    type = config.get('type')
    learning_rate = config.get('learning_rate')
    weight_decay = config.get('weight_decay', 0)
    if type == 'SGD':
        momentum = config.get('momentum', 0)
        return optim.SGD(model.parameters(), lr=learning_rate, momentum=momentum, weight_decay=weight_decay)
    elif type == 'Adam':
        return optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    else:
        raise Exception(f'Unknown optimizer: {type}')
