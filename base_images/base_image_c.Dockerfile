# base image for C projects
FROM ubuntu:20.04

# set timezone
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# install common system packages
RUN apt-get update && apt-get install -y git make sudo wget curl build-essential python curl lsb-release software-properties-common

# create user and group
ARG cuid=1000
ARG cgid=1000
ARG cuidname=fuzzer
ARG cgidname=fuzzer

RUN groupadd -g $cgid $cgidname && useradd -m -u $cuid -g $cgidname -s /bin/bash $cuidname && \
    echo $cuidname ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$cuidname && \
    chmod 0440 /etc/sudoers

# install clang version 14
RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && sudo ./llvm.sh 14
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-14 100 && \
update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-14 100 && \
update-alternatives --install /usr/bin/c++ c++ /usr/bin/clang++-14 100 && \
update-alternatives --install /usr/bin/cc cc /usr/bin/clang-14 100 && \
update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-14 100 && \
update-alternatives --install /usr/bin/llvm-ar llvm-ar /usr/bin/llvm-ar-14 100 && \
update-alternatives --install /usr/bin/llvm-nm llvm-nm /usr/bin/llvm-nm-14 100 && \
update-alternatives --install /usr/bin/llvm-ranlib llvm-ranlib /usr/bin/llvm-ranlib-14 100 && \
update-alternatives --install /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-14 100 && \
update-alternatives --install /usr/bin/llvm-objdump llvm-objdump /usr/bin/llvm-objdump-14 100

# clone AFL++ repository
WORKDIR /home/$cuidname
RUN git clone https://github.com/AFLplusplus/AFLplusplus

#Build AFL++
WORKDIR /home/$cuidname/AFLplusplus
RUN LLVM_CONFIG=llvm-config-14 make -j$(nproc)

ENV AFL_SKIP_CPUFREQ=1
ENV AFL_TRY_AFFINITY=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

USER $cgidname

WORKDIR /

ENTRYPOINT /bin/bash