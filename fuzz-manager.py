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

    def __init__(self, project_path, language=None, dockerfile=None):
        self.project_path = project_path.rstrip('/')
        self.language = language
        self.dockerfile = dockerfile

        self.name = os.path.basename(self.project_path)
        self.image_name = '{project}_image'.format(project=self.name)
        self.container_name = '{project}_fuzz'.format(project=self.name)
        
        self.is_image_builded = False
        self.container = None

    # TODO maybe these functions should not check that the container exists and the image is builded
    # to avoid repetitions. Maybe these checks should be done by the calling functions

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

    def create_container(self, env=None):
        """Starts the container"""
        if self.is_container_created():
            logger.info("Could not create the container, because it already exists")
            return True

        if not self.is_image_builded:
            # TODO correctly handle this event (maybe return error or False)
            self.build_project_image()

        try:
            self.container = docker_client.containers.create(image=self.image_name, name=self.container_name, environment=env)
        # Ignore ImageNotFound because we first have checked that image exists
        except docker.errors.APIError as error:
            logger.error("Could not create docker container: %s", error)
            return False

        logger.info("Docker container created successfully")
        return True

    def start_container(self):
        """Start the container"""
        if not self.is_container_created():
            logger.error("Could not start the container, because it does not exist")
            return False

        if self.container.status == 'running':
            logger.info("The container is running")
            return True

        # TODO wait for container or run it in attach mode
        try:
            self.container.start()
        except docker.errors.APIError as err:
            logger.error("Could not start the container: %s", err)
            return False

        logger.info("Docker container started successfully")
        return True

    def run_fuzzers(self):
        """Run fuzzers in the container"""
        pass
    
    def attach_container(self):
        """Attaches the container for shell function"""
        pass

    def stop_container(self):
        """Stops the container"""
        if not self.is_container_created():
            logger.info("Could not stop the container, because it does not exist")
            return True

        if self.container.status == 'exited':
            logger.info("The container is exited")
            return True

        try:
            self.container.stop()
        except docker.errors.APIError as err:
            logger.error("Could not stop the container: %s", err)
            return False

        return True

    def is_base_image_builded(self):
        """Checks that base_image exists"""
        try:
            docker_client.images.get('base_image_{language}'.format(language=self.language))
            return True
        except docker.errors.ImageNotFound:
            return False

    def is_container_created(self):
        """checks that the container exists and if true sets self.container field"""
        if self.container == None:
            try:
                self.container = docker_client.containers.get(self.container_name)
            except docker.errors.NotFound:
                return False

        return True

def main():
    """Gets subcommand from program arguments and performs it."""
    logging.basicConfig(level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    
    if args.command == 'build_base_images':
        build_base_images(args)
    elif args.command == 'build_fuzzers':
        build_fuzzers(args)
    elif args.command == 'run_fuzzers':
        run_fuzzers(args)
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
                                      help='Build with specific sanitizer. Default is address')
    
    # TODO  add some arguments to adjust the process of fuzzing
    run_fuzzers_parser = subparsers.add_parser('run_fuzzers', help='Run fuzzers for a project')
    run_fuzzers_parser.add_argument('project_path', help='Path to the project')
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

    # run the container
    if not project.create_container(env=['SANITIZER={sanitizer}'.format(args.sanitizer)]) or not project.start_container():
        return
    
    # run build.sh inside of the container
    try:
        # TODO determine the best way to run build.sh in the container. Maybe we should run it detach mode
        # or run it as ENTRYPOINT in dockerfile
        project.container.exec_run(cmd=['./build.sh'])
    except docker.errors.APIError as err:
        logger.error("Could not run build.sh in the container: %s", err)
        return

    # Think it is better to stop the container and start it when needed
    project.stop_container()

def run_fuzzers(args):
    """Run the process of fuzzing in the container"""
    project = Project(args.project_path)
    
    if not project.is_container_created():
        logger.error('Could not run fuzzing, because there is no target container.\n \
                      You should first run `python {file_name} build-fuzzers {project}`'.format(os.path.realpath(__file__), project))
        return
    
    if not project.start_container():
        return

    project.run_fuzzers()
    project.stop_container()

main()