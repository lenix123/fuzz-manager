import argparse
import docker
import logging
import os

HOME_DIR = os.path.dirname(os.path.realpath(__file__))

BASE_IMAGE_C_NAME = 'base_image_c'
BASE_IMAGE_GO_NAME = 'base_image_go'

logger = logging.getLogger('fuzz-manager')
docker_client = docker.from_env()

class Project:
    """Class representing a project"""

    def __init__(self, project_path, language, dockerfile):
        self.project_path = project_path.rstrip('/')
        self.language = language
        self.dockerfile = dockerfile

        self.name = os.path.basename(self.project_path)
        self.image_name = '{project}_image'.format(project=self.name)
        self.container_name = '{project}_fuzz'.format(project=self.name)
        
        self.is_image_builded = False
        self.container = None

    def build_project_image(self):
        """Builds docker image for the project"""
        if not self.is_base_image_builded():
            logger.error("Base image should be builded first. Run `build_base_images`")
            return False

        # TODO we assume that dockerfile is located in root directory of the project,
        # but it may be not the case
        # TODO strengthen the validation of the path
        if not os.path.isdir(self.project_path):
            logger.error('the specified path for the project does not exist: %s', self.project_path)
            return False

        # default is Dockerfile
        dockerfile_path = os.path.join(self.project_path, self.dockerfile)
        if not os.path.isfile(dockerfile_path):
            logger.error('the specified path for the dockerfile does not exist: %s', dockerfile_path)
            return False

        try:
            # TODO show docker logging in realtime
            logger.info('Building project image...')
            docker_client.images.build(tag=self.image_name, path=self.project_path, dockerfile=self.dockerfile)
        except docker.errors.BuildError or docker.errors.APIError:
            logger.error('Docker build failed.')
            return False

        self.is_image_builded = True
        logger.info('Docker image for the project builded successfully')
        return True

    def is_base_image_builded(self):
        """Checks that base_image exists"""
        try:
            docker_client.images.get('base_image_{language}'.format(language=self.language))
            return True
        except docker.errors.ImageNotFound:
            return False

    def run_container(self):
        """Runs the container"""
        if not self.is_image_builded:
            # TODO correctly handle this event (maybe return error or False)
            self.build_project_image()

        try:
            # TODO wait for container or run it in attach mode
            self.container = docker_client.containers.run(image=self.image_name, detach=True, name=self.container_name)
        # Ignore ContainerError because running in the detach mode
        # Ignore ImageNotFound because we first have checked that image exists
        except docker.errors.APIError as error:
            logger.error("Could not run docker container: %s", error)
            return False

        logger.info("Docker container started successfully")
        return True

    def start_container(self):
        """Start the container"""
        pass
    
    def attach_container(self):
        """Attaches the container for shell function"""
        pass

    def stop_container(self):
        """Stops the container"""
        pass

def main():
    """Gets subcommand from program arguments and performs it."""
    logging.basicConfig(level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    
    if args.command == 'build_base_images':
        build_base_images(args)
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

    build_fuzzers_parser = subparsers.add_parser('build_fuzzers', help='Build fuzzers for a project.')
    build_fuzzers_parser.add_argument('project_path', help='Path to the project')
    build_fuzzers_parser.add_argument('--dockerfile', default='Dockerfile', help='Dockerfile name. Default is `Dockerfile`')
    build_fuzzers_parser.add_argument('--language', default='c', help='the language of the project. Default is c')
    build_fuzzers_parser.add_argument('--sanitizer', choices=['address', 'undefined', 'coverage', 'none'], default='address',
                                      help='default is address sanitizer. Default is address')
    
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

def build_fuzzers(args):
    """Starts project container and prepares everything for fuzzing"""
    project = Project(args.project_path, args.language, args.dockerfile)

    if not project.is_image_builded and not project.build_project_image():
        return

    # TODO in future commands we may don't want to run container, but instead start it if container exists
    # maybe it is better to separate run to create and start functions
    if project.container == None and not project.run_container():
        return

    # TODO run in the created container setup.sh

main()