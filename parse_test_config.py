import argparse

def create_parser():
    parser = argparse.ArgumentParser(description="Execute tests")

    # Add a flag for different schemas, including "all" as the default
    parser.add_argument('--schema', choices=['OGB_MAG', 'Synthea', 'DigitalInfra', 'all'],
                        default='all', help='Choose a schema (default: all)')

    # Add a flag for whether to run with weights and biases
    parser.add_argument('--wandb', dest='wandb', action='store_true', help='Use Weights and Biases for test logging (Default)')
    parser.add_argument('--no-wandb', dest='wandb', action='store_false', help='Disable Weights and Biases for test logging')
    parser.set_defaults(wandb=True)

    return parser
