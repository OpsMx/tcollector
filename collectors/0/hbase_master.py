#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import time

try:
    import json
except ImportError:
    json = None

from collectors.lib import utils
from collectors.lib.hadoop_http import HadoopHttp
from collectors.etc import opsmxconf

if opsmxconf.OVERRIDE:
    COLLECTION_INTERVAL=opsmxconf.GLOBAL_COLLECTORS_INTERVAL
else:
    COLLECTION_INTERVAL=60

EXCLUDED_CONTEXTS = ('regionserver', 'regions', 'regionserverdynamicstatistics' , 'rpcstatistics-33985' ,)


class HBaseMaster(HadoopHttp):
    """
    Class to get metrics from Apache HBase's master

    Require HBase 0.96.0+
    """

    def __init__(self):
        super(HBaseMaster, self).__init__('hbase', 'master', 'localhost', 60010)

    def emit(self):
        current_time = int(time.time())
        metrics = self.poll()
        for context, metric_name, value in metrics:
            if any(c in EXCLUDED_CONTEXTS for c in context):
                continue
            self.emit_metric(context, current_time, metric_name, value)


def main(args):
    utils.drop_privileges()
    if json is None:
        utils.err("This collector requires the `json' Python module.")
        return 13  # Ask tcollector not to respawn us
    hbase_service = HBaseMaster()
    while True:
        hbase_service.emit()
        time.sleep(COLLECTION_INTERVAL)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

