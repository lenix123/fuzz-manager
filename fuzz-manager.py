import argparse
import docker
import logging
import os

HOME_DIR = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger('fuzz-manager')
docker_client = docker.from_env()

def main():
    """Gets subcommand from program arguments and performs it."""
    logging.basicConfig(level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    
    if args.command == 'build_base_images':
        build_base_images(args)
    elif args.command == 'build_project_image':
        build_project_image(args)
    elif args.command == 'build_fuzzers':
        build_fuzzers(args)
    else:
        parser.print_help()

def get_parser():
    """Returns an argparse parser."""
    parser = argparse.ArgumentParser(prog='fuzz-manager.py', description='manager of fuzzing process')
    subparsers = parser.add_subparsers(dest='command')

    build_base_images_parser = subparsers.add_parser('build_base_images', help='Build base images.')
    build_base_images_parser.add_argument('--only', choices=['c', 'go'], default=None, help='build base image only for specific language')

    build_project_image_parser = subparsers.add_parser('build_project_image', help='Build project image.')
    build_project_image_parser.add_argument('project')

    build_fuzzers_parser = subparsers.add_parser('build_fuzzers', help='Build fuzzers for a project.')
    build_fuzzers_parser.add_argument('project')
    build_fuzzers_parser.add_argument('--sanitizer', choices=['address', 'undefined', 'coverage', 'none'], default='address',
                                      help='default is address sanitizer')
    
    return parser

def build_base_images(args):
    """Builds base images for C and Go projects."""
    dockerfile_path = os.path.join(HOME_DIR, 'base_images')
    try:
        logger.info('Building base images...')
        if args.only == 'c' or args.only == None:
            docker_client.images.build(tag='base_image_c', path=dockerfile_path, dockerfile='base_image_c.Dockerfile')
        if args.only == 'go' or args.only == None:
            docker_client.images.build(tag='base_image_go', path=dockerfile_path, dockerfile='base_image_go.Dockerfile')
    except docker.errors.BuildError or docker.errors.APIError:
        logger.error('Docker build failed.')

    logger.info('Docker image builded successfully')


def build_project_image(args):
    pass

def build_fuzzers(args):
    pass

main()