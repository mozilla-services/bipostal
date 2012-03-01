<%
    info = pageargs.get('info')
%>
<style>
p {font: 80% arial}
</style>
<div id="header">
<p>This message was sent to the alias you used for ${info.get('origin', 'Unknown sender')}.</p>
</div>
<div id="body">
<hr>
<pre>
