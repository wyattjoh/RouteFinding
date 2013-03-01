Assignment 3: Part 1

Files included:
	async.py
		- provides:
			function: run_async
	batch.txt
		- contains some batch tests
	digraph.py
		- provides:
			class: DiGraph
			function: least_cost_path
	display.py
	edmonton-roads-2.0.1.txt
	readgraph.py
	readme.txt
	server.py
		- Main application framework, see below for instructions

To import as module:
	>>> from server import least_cost_path
	>>> from server import cost_distance

To run as standalone with input from stdin:
	>> python3 server.py stdin edmonton-roads-2.0.1.txt < batch-file.txt

To run as standalone with input from keyboard:
	>> python3 server.py stdin edmonton-roads-2.0.1.txt