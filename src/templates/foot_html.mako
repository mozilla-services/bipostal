<%
    info = pageargs.get('info', {})
%>
</pre>
</div>
<div id="footer">
<hr>
<p>To temporarily disable or prevent more notifications from ${info.get('origin', 'this sender')}, 
go to:<a href="${info.get('manageurl', 'http://bipostal.diresworb.org/#template')}">${info.get('manageurl', 'http://bipostal.diresworb.org/#template')}"></a></p>
</div>
