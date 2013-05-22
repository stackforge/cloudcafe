"""
Copyright 2013 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class InstanceClientConstants:
    LAST_REBOOT_TIME_FORMAT = '%Y-%m-%d %H:%M'
    LAST_REBOOT_TIME_FORMAT_GENTOO = '%b %d %H:%M %Y'
    LINUX_OS_FAMILY = 'linux'
    PING_IPV4_COMMAND_LINUX = 'ping -c 3 '
    PING_IPV6_COMMAND_LINUX = 'ping6 -c 3 '
    PING_IPV4_COMMAND_WINDOWS = 'ping '
    PING_IPV6_COMMAND_WINDOWS = 'ping6 '
    PING_PACKET_LOSS_REGEX = '(\d{1,3})\.?\d*\%.*loss'
