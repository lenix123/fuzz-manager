import argparse
import docker
import logging
import os

HOME_DIR = os.path.dirname(os.path.realpath(__file__))

BASE_IMAGE_C_NAME = 'base_image_c'
BASE_IMAGE_GO_NAME = 'base_image_go'

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
    build_project_image_parser.add_argument('project_path', help='Path to the project')
    build_project_image_parser.add_argument('--dockerfile', default='Dockerfile', help='Dockerfile name')
    build_project_image_parser.add_argument('--language', default='c', help='the language of the project')

    build_fuzzers_parser = subparsers.add_parser('build_fuzzers', help='Build fuzzers for a project.')
    build_fuzzers_parser.add_argument('project')
    build_fuzzers_parser.add_argument('--sanitizer', choices=['address', 'undefined', 'coverage', 'none'], default='address',
                                      help='default is address sanitizer')
    
    return parser

def build_base_images(args):
    """Builds base images for C and Go projects."""
    dockerfile_path = os.path.join(HOME_DIR, 'base_images')
    try:
        # TODO show docker logging in realtime
        logger.info('Building base images...')
        if args.only == 'c' or args.only == None:
            docker_client.images.build(tag=BASE_IMAGE_C_NAME, path=dockerfile_path,
                                       dockerfile='{base_image}.Dockerfile'.format(base_image=BASE_IMAGE_C_NAME))
        if args.only == 'go' or args.only == None:
            docker_client.images.build(tag=BASE_IMAGE_GO_NAME, path=dockerfile_path,
                                       dockerfile='{base_image}.Dockerfile'.format(base_image=BASE_IMAGE_GO_NAME))
    except docker.errors.BuildError or docker.errors.APIError:
        logger.error('Docker build failed.')
        return

    logger.info('Docker image builded successfully')


def build_project_image(args):
    # TODO we assume that dockerfile is located in root directory of the project,
    # but it may be not the case
    project_path = args.project_path.rstrip('/')
    # TODO strengthen the validation of the path
    if not os.path.isdir(project_path):
        logger.error('the specified path for the project does not exist: %s', project_path)
        return

    # default is Dockerfile
    dockerfile = args.dockerfile
    dockerfile_path = os.path.join(project_path, dockerfile)
    if not os.path.isfile(dockerfile_path):
        logger.error('the specified path for the dockerfile does not exist: %s', dockerfile_path)
        return
    
    project_name = os.path.basename(project_path)

    try:
        # TODO show docker logging in realtime
        logger.info('Building project image...')
        docker_client.images.build(tag='{project}_image'.format(project=project_name), path=project_path, dockerfile=dockerfile)
    except docker.errors.BuildError or docker.errors.APIError:
        logger.error('Docker build failed.')
        return

    logger.info('Docker image for the project builded successfully')

def build_fuzzers(args):
    pass

main()