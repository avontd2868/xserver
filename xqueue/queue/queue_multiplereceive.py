#!/usr/bin/env python
import queue_common
import threading 
import requests
import pika
import json
from lxml import etree

#------------------------------------------------------------
# Encapsulation of a single RabbitMQ connection and
#	channel per thread
#------------------------------------------------------------
class SingleChannel(threading.Thread):
	def __init__(self, workerID):
		threading.Thread.__init__(self)
		self.workerID = workerID
		self.workerURL = queue_common.WORKER_URLS[workerID]

	def run(self):
		print ' [%d] Starting worker %d at %s' % (self.workerID, self.workerID, self.workerURL)
		connection = pika.BlockingConnection(
						pika.ConnectionParameters(host=queue_common.RABBIT_HOST))
		channel = connection.channel()
		channel.queue_declare(queue=queue_common.RABBIT_QUEUE_NAME)
		channel.basic_qos(prefetch_count=1)
		channel.basic_consume(self._callback,
							  queue=queue_common.RABBIT_QUEUE_NAME)
		channel.start_consuming()
		
	def _callback(self, ch, method, properties, body):
		print ' [%d] Got work from %s, dispatched to %s' %\
			( self.workerID, queue_common.RABBIT_QUEUE_NAME, self.workerURL )
		work = json.loads(body)
		header = json.loads(work.pop(queue_common.HEADER_TAG))
		
		# Send task to external server synchronously
		try:
			r = requests.post(self.workerURL, data=work)
		except Exception as err:
			msg = 'Error %s - cannot connect to worker at %s' % (err, self.workerURL)
			raise Exception(msg)

		# Decide if the response from the worker node is satisfactory.
		#	If yes, send back to the LMS
		self._post_to_lms(header, r.text)

		# Send job acknowledgement to queue 
		ch.basic_ack(delivery_tag = method.delivery_tag)

	# This is currently a placeholder for writing back to LMS
	#------------------------------------------------------------
	def _post_to_lms(self, header, rstr):
		returnURL = 'http://18.189.69.130:8000' # NOTE: hard-coded to my LMS sandbox
		payload = header
		payload.update({'response': rstr})
		requests.post(returnURL+'/modx2/', data=payload)

#------------------------------------------------------------
# Instantiate RabbitMQ consumers corresponding 1:1 with
#	each worker server
#------------------------------------------------------------
def main():
	print ' [*] Starting handlers for %s (%s). Press CTRL+C to exit' %\
		(queue_common.SERVER_NAME, queue_common.SERVER_DESC)

	num_workers = len(queue_common.WORKER_URLS)
	channels = [None]*num_workers
	for wid in range(num_workers):
		channels[wid] = SingleChannel(wid)
		channels[wid].start()
		
	channels[0].join() # Wait forever. To do: Trap Ctrl+C, not assume num_workers > 0

if __name__ == '__main__':
	main()