# Webpage Loader

### Usage

```
python page_load_wrapper.py [pages_filename] [num_iterations] [output_directory]
```

### Requirements

__Python Libraries__
* websocket-client
* simplejson
* beautifulsoup4

Run:
```
pip install websocket-client simplejson beautifulsoup4 --user
```

### Miscellaneous

#### Device emulation when using Chrome desktop.

Set an environment variable `EMULATE_DEVICE` to "Google Nexus 6"

```
export EMULATE_DEVICE="Google Nexus 6"
```

#### Use different devices

By default, the tool uses a Nexus 6 phone to load pages. However, in some circumstances, we want to use the desktop version instead. To do so, add the `--use-device` command-line args to `page_load_wrapper.py` script.

Available devices:
* ubuntu
* mac
* Nexus\_6
* Nexus\_6\_2

#### Resource collection

