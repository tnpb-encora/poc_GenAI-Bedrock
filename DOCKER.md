# Docker execution instructions
****

This project has a Dockerfile and a docker-compose.yml that allows you to build and run it as a container.
This document will guide you on how to do it.

## Building your image


```
docker build -t <tagname>:<tagversion> .
```
The -t option in the command will allow you to create the image with a tag name and tag version, split by a colon (:).

After tagging your image, you will have to inform the path to the Dockerfile. If you are in the same directory as the Dockerfile
you can use a dot (.), otherwise, use the whole path to it.

> [!TIP]
> If you have trouble with downloading dependencies and installing requirements, this may be due to network configuration.
> 
> When docker builds an image, it uses his own bridged network interface to access the internet and download whatever the project needs.
> Sometimes, this network fails to access the internet and blocks the building process. This can be due to firewall settings or 
> other network reasons. 
> 
> You can change the network configuration by telling docker to use your host network. To do so, at the end of the build command, add the option ```--network=host```.

> [!NOTE]
> It is possible to build a Docker image using docker-compose. Altough, in this project, the docker-compose is not set to allow it.


##  Handling the image

One of Docker purposes is to make your project portable, gathering all it needs into an image that generates a container.
So, when you build your project into an image, you should be able to deliver it to other environments without much trouble. 
Here are your options to do it.

### Docker Hub

The Docker Hub is a proprietary registry, managed by Docker, that hosts most of the Docker images around the internet. There, you can find official 
repositories from almost every big tech company that offers its software in containers. 

You can have an account there too. If it's the case, you are able to publish your recent built image to the Docker Hub and access it everywhere.

> [!IMPORTANT]
> When you create a free Docker Hub account, you are able to have a single private repository. So, if you want to protect your code, you must take it into account.

To publish your image to a repository in Docker Hub, you have to log into your account through Docker.

```
docker login -u <username>
```
The prompt will ask you to enter your password. Enter it and you will be logged in. 

It is important to know that Docker Hub is the standard registry for Docker. That's why you don't need to inform its URL in the docker login command.
If you have another registry you want to publish your image, you should use the following command:

```
docker login -u <username> <your_registry>
```

You are also able to inform your password through a file:

```
cat ~/my-password-file.txt | docker login -u <username> --password-stdin
```
Or:
```
cat ~/my-password-file.txt | docker login -u <username> <your_registry> --password-stdin
```

Now you are logged in, you can push your image to your repository. You should consider that changes the way you build your image.
Now, you have to tag your image with your repository name. Like this:

```
docker build -t <my_repository_name>/<my_tag_name>:<my_tag_version> .
```

This way, you can publish it with no trouble, using the command:

```
docker push <my_repository_name>/<my_tag_name>:<my_tag_version>
```

After running this command, the image will be pushed into the Docker Hub repository, and you will be able to access it anywhere.

### Turning your image into a file

If you don't have access to the Docker Hub, you can transfer your image from a place to another by turning it into a tar file.

To do so, you have to run:

```
docker save -o ~/path/to/tarfile <tagname>:<tagversion>
```

This command will get your image and transform it into a tar file that will be output in the path you informed. This tar file
can be copyied to other places and extracted there, using the following command:

```
docker load -i ~/path/to/tarfile
```

After that, you can check your image in the new location with

```
docker images
```

## Docker Compose

The docker-compose is a framework that helps, among other things, to handle the lifecycle of the container. With it, you can create 
a file that will save all the configuration you need to make sure your container runs exactly the way you want.

### Installation

You can install the docker-compose by curling it from its repository, using the following commands:

```
sudo curl -L "https://github.com/docker/compose/releases/download/<version>/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

You can check its last version [here](https://github.com/docker/compose/releases).

To check if the installation was successful, use:

```
docker-compose version
```

### Configuring a container

You can configure what you need to run a container inside the docker-compose.yml file. 
This project has a docker-compose.yml with some of the most common settings in the framework.
Here is a brief explanation of them:

* `version`: is the YAML version of the docker-compose file.
* `services`: the services that the file will handle. You can handle more than one container in the same file, as well as network services, volumes services etc.
* `poc_genAI`: name of the service - in this case is a container.
* `image`: the Docker image in which the container will be based. It can be pulled from an online registry, like Docker Hub, or locally.
* `container_name`: the name of the container.
* `hostname`: this is how the network will see this container. This is helpful when having to track the container interation with other services.
* `restart`: defines how the container will behave after termination. It can be `no`, `always`, `on-failure`, or `unless-stopped`.
* `network_mode`: this defines what kind of network interface the container will use: `host` or `bridge`. If suppressed, the default is `bridge`.
* `volumes`: defines volumes from and to the container. Everything before colon (:) refers to the host. Everything after, refers to the container. If opens a communication through file system between host and container.
* `environment`: defines Environment variables in the container. You can define it directly in the docker-compose.yml or via a .env file.

Other common tag is `ports`. It will map a port from host that will be redirected to the container. It is defined by 
```
ports:
    - XXXX:XXXX
```

Everything left of colon (:) refers to host. Everything right, refers to container. 

Since we're using the `network_mode: host` the ports are not necessary. The container will use the port exposed in the Dockerfile.

### Starting and terminating a container

The docker-compose.yml makes your life easier when it comes to handle a container lifecycle. 
Of course, you always can use `docker run -d` or `docker stop`. But if you need to remove the container, the `docker stop` won't cover it.
Or, if you need to start your container again, after removing it, you have to remember and inform all the options again.

Better way is to join both approaches, using docker commands for inspection purposes, and docker-compose commands for container lifecycle. 

After configuring your docker-compose.yml file, you can start your container by running:

```
docker-compose up -d
```

Make to be in the same directory as the docker-compose.yml file. Otherwise, you can run:

```
docker-compose -f /path/to/docker-compose.yml up -d
```

Use the `-d` option to run the container in detached mode. If you don't use it, your terminal will be attached to the container and exiting will terminate it.

In the same way, you can terminate your container by running:

```
docker-compose down
```
Or:

```
docker-compose -f /path/to/docker-compose.yml down
```

This command not only stops the container, but it also removes it. So, when you start it again, there won't be any name conflict.

## Other important Docker commands

### Inspect

The `docker inspect <container>` command will show a complete report about the container information. 

### Processes

Running `docker ps` will bring all containers running in that Docker Engine. 

Running `docker ps -a` will show also the containers stopped. If you remove a container, you won't be able to see it.

### Logs

You can check your container logs by using `docker logs -f <container>`. The `-f` option will follow the output. Check `docker logs -h` for help.

Also, you can use docker-compose to check logs, by running `docker-compose logs -f`. Attention to this `-f` option. When used right after the `docker-compose` it indicates 
the path to the docker-compose.yml. If you use it after the `logs` option, will follow the output.

In both options, you can add the option `-n <number>` to indicate the amount of lines you want to check in the output.

### Execute

You can execute a command inside the container from the host. There are several situation in which this is important.
You can even run a bash terminal to access the container.

The command to do it is `docker exec -it <container> <command>`.

The option `-i` opens an interactive mode, keeping STDIN open. And the option `-t` will allocate a pseudo Terminal in the container.

To execute a bash terminal, you can run `docker exec -it <container> /bin/bash`. In general, `/bin/bash` works for the most of images.
But you can also find `/bin/sh`, or just `/sh`. So, make sure you know what kind of shell is being used by your image.