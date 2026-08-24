"""Tests for k8s node discovery parsing (pure functions)."""
from __future__ import annotations

from app.discovery import os_flavor_from, parse_nodes_output

SAMPLE = """NAME  STATUS  ROLES  AGE  VERSION  INTERNAL-IP  EXTERNAL-IP  OS-IMAGE  KERNEL-VERSION  CONTAINER-RUNTIME
hblf-master01  Ready  control-plane  156d  v1.28.10  10.255.3.197  <none>  CentOS Linux 8  5.10.134-19.2.an8.x86_64  containerd://1.7.27
lf-gpu-4-1  Ready  <none>  156d  v1.28.10  10.255.4.1  <none>  YDLinux  5.10.134-19.2.al8.x86_64  containerd://1.7.27
notready-node  NotReady  <none>  10d  v1.28.10  10.255.9.9  <none>  Ubuntu 22.04.4  LTS  5.15.0-91-generic  containerd://1.7.27
"""


def test_parse_nodes_output():
    nodes = parse_nodes_output(SAMPLE)
    assert len(nodes) == 3
    assert nodes[0]["hostname"] == "hblf-master01"
    assert nodes[0]["ip"] == "10.255.3.197"
    assert nodes[0]["os_image"] == "CentOS Linux 8"
    assert nodes[1]["hostname"] == "lf-gpu-4-1"
    assert nodes[1]["ip"] == "10.255.4.1"
    assert nodes[1]["os_image"] == "YDLinux"
    assert nodes[2]["status"] == "NotReady"


def test_parse_ignores_header():
    nodes = parse_nodes_output("NAME  STATUS  ROLES  AGE  VERSION  INTERNAL-IP  EXTERNAL-IP  OS-IMAGE")
    assert nodes == []


def test_os_flavor_mapping():
    assert os_flavor_from("CentOS Linux 8") == "centos"
    assert os_flavor_from("YDLinux") == "centos"        # RHEL-family
    assert os_flavor_from("Alibaba Cloud Linux 3") == "centos"
    assert os_flavor_from("Ubuntu 22.04.4 LTS") == "ubuntu"
