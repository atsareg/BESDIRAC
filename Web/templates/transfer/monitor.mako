# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<%inherit file="/diracPage.mako" />

<%def name="head_tags()">
${ h.javascript_link( "/javascripts/transfer/reqmgr.js" ) }
${ h.javascript_link( "/javascripts/transfer/monitor.js" ) }
</%def>

<%def name="body()">
<script type="text/javascript">
  initMonitor();
</script>
</%def>

