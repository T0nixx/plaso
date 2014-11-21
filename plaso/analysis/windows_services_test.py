#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2014 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the windows services analysis plugin."""

import unittest

from dfvfs.path import fake_path_spec

from plaso.analysis import test_lib
from plaso.analysis import windows_services
from plaso.engine import queue
from plaso.engine import single_process
from plaso.events import windows_events
from plaso.parsers import winreg


class WindowsServicesTest(test_lib.AnalysisPluginTestCase):
  """Tests for the Windows Services analysis plugin."""

  SERVICE_EVENTS = [
      {u'path': u'\\ControlSet001\\services\\TestbDriver',
       u'text_dict': {u'ImagePath': u'C:\\Dell\\testdriver.sys', u'Type': 2,
                      u'Start': 2, u'ObjectName': u''},
       u'timestamp': 1346145829002031},
      # This is almost the same, but different timestamp and source, so that
      # we can test the service de-duplication.
      {u'path': u'\\ControlSet003\\services\\TestbDriver',
       u'text_dict': {u'ImagePath': u'C:\\Dell\\testdriver.sys', u'Type': 2,
                      u'Start': 2, u'ObjectName': u''},
       u'timestamp': 1346145839002031},
  ]

  def _CreateTestEventObject(self, service_event):
    """Create a test event object with a particular path.

    Args:
      service_event: A hash containing attributes of an event to add to the
                     queue.

    Returns:
      An EventObject representing the service to be created.
    """
    test_pathspec = fake_path_spec.FakePathSpec(
        location=u'C:\\WINDOWS\\system32\\SYSTEM')
    event_object = windows_events.WindowsRegistryServiceEvent(
        service_event[u'timestamp'], service_event[u'path'],
        service_event[u'text_dict'])
    event_object.pathspec = test_pathspec
    return event_object

  def testSyntheticKeys(self):
    """Test the plugin against mock events."""
    event_queue = single_process.SingleProcessQueue()

    # Fill the incoming queue with events.
    test_queue_producer = queue.ItemQueueProducer(event_queue)
    events = [self._CreateTestEventObject(service_event)
              for service_event
              in self.SERVICE_EVENTS]
    test_queue_producer.ProduceItems(events)
    test_queue_producer.SignalEndOfInput()

    # Initialize plugin.
    analysis_plugin = windows_services.AnalyzeWindowsServicesPlugin(event_queue)

    # Run the analysis plugin.
    knowledge_base = self._SetUpKnowledgeBase()
    analysis_report_queue_consumer = self._RunAnalysisPlugin(
        analysis_plugin, knowledge_base)
    analysis_reports = self._GetAnalysisReportsFromQueue(
        analysis_report_queue_consumer)

    self.assertEquals(len(analysis_reports), 1)

    analysis_report = analysis_reports[0]

    expected_text = (
        u'Listing Windows Services\n'
        u'TestbDriver\n'
        u'\tImage Path    = C:\\Dell\\testdriver.sys\n'
        u'\tService Type  = File System Driver (0x2)\n'
        u'\tStart Type    = Auto Start (2)\n'
        u'\tService Dll   = \n'
        u'\tObject Name   = \n'
        u'\tSources:\n'
        u'\t\tC:\\WINDOWS\\system32\\SYSTEM:'
        u'\\ControlSet001\\services\\TestbDriver\n'
        u'\t\tC:\\WINDOWS\\system32\\SYSTEM:'
        u'\\ControlSet003\\services\\TestbDriver\n\n')

    self.assertEquals(expected_text, analysis_report.text)
    self.assertEquals(analysis_report.plugin_name, 'windows_services')

  def testRealEvents(self):
    """Test the plugin against real events from the parser."""
    parser = winreg.WinRegistryParser()
    # We could remove the non-Services plugins, but testing shows that the
    # performance gain in negligible.

    knowledge_base = self._SetUpKnowledgeBase()
    test_path = self._GetTestFilePath(['SYSTEM'])
    event_queue = self._ParseFile(parser, test_path, knowledge_base)

    # Run the analysis plugin.
    analysis_plugin = windows_services.AnalyzeWindowsServicesPlugin(event_queue)
    analysis_report_queue_consumer = self._RunAnalysisPlugin(
        analysis_plugin, knowledge_base)
    analysis_reports = self._GetAnalysisReportsFromQueue(
        analysis_report_queue_consumer)

    report = analysis_reports[0]
    self.assertEquals(len(report.text), 136830)


if __name__ == '__main__':
  unittest.main()
