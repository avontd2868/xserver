#!/usr/bin/python
#------------------------------------------------------------
# File: pyxserver_wsgi.py
# Date: 2012 July 24
# Author: T. H. Kim <kimth@stanford.edu>
#
# Re-wrapped pyxserver to be compatible with nginx + (uWSGI or gunicorn)
#
# Run me with (may need sudo privilege for logging):
#	uWSGI: 
#		uwsgi --socket 127.0.0.1:3031 --wsgi-file /path/to/pyxserver_wsgi.py --processes 4
#	gunicorn:
#		gunicorn -w 4 -b 127.0.0.1:3031 pyxserver_wsgi:application
#
#------------------------------------------------------------

import json
from time import localtime, strftime 
from urlparse import parse_qs

import pyxserver

def do_GET(data):
	return "Hey, the time is %s" % strftime("%a, %d %b %Y %H:%M:%S", localtime())

def do_POST(data):
	post = parse_qs(data) # Dict

	# Parse ExternalResponse interface
	cmd = str(post['edX_cmd'][0]).strip()
	tests = post['edX_tests'][0]
	processor = post['processor'][0].strip()
	print ' [*] cmd: %s' % cmd
	#print ' [*] tests: %s' % tests
	#print ' [*] processor: %s' % processor
	
	if cmd == 'get_score':
		student_response = json.loads(post['edX_student_response'][0])[0]
		award, message = pyxserver.run_code_sandbox(processor, student_response, tests)

		reply_template = "<edxgrade><awarddetail>%s</awarddetail><message><![CDATA[%s]]></message><awarded></awarded></edxgrade>"
		reply = reply_template % (award, message)

	elif cmd == 'get_answers':
		expected, message = pyxserver.run_code_sandbox(processor, "", tests, getans=True)

		reply_template = "<edxgrade><message><![CDATA[%s]]></message><expected><![CDATA[%s]]></expected></edxgrade>"
		reply = reply_template % (message, json.dumps([expected]))

	return reply 

# Entry point
def application(env, start_response):

	# Handle request
	method = env['REQUEST_METHOD']
	data = env['wsgi.input'].read()

	print '-'*60
	print method

	handlers = { 'GET' : do_GET,
				 'POST': do_POST,
				 }
	if method in handlers.keys():
		reply = handlers[method](data)
		print ' [*] reply:\n%s\n' % reply
		start_response('200 OK', [('Content-Type', 'text/html')])
		return reply
	else:
		start_response('404 Not Found', [('Content-Type', 'text/plain')])
		return ''