from jinja2 import Environment, FileSystemLoader
import yaml
import urllib.request
import os
import os.path
import tarfile

config_data = yaml.load(open('./config.yaml'))
env = Environment(loader = FileSystemLoader('./templates'), trim_blocks=True, lstrip_blocks=True)

# Make sure the needed dependencies for this script and running Zookeeper and Kafka are present
def env_prep():
    print("Prepping environment for installer")

# Download and extract the service binaries to the configured location
def download_and_extract(service_name, conf_prefix):
    download_path = os.path.join(config_data[conf_prefix + '_base_dir'], os.path.basename(config_data[conf_prefix + '_download_url']))
    if os.path.exists(download_path):
        print(service_name + " is already downloaded at: " + download_path + " ... skipping")
    else:
        # Create the base_dir if it does not exist
        if not os.path.exists(config_data[conf_prefix + '_base_dir']):
            os.system("mkdir -p " + config_data[conf_prefix + '_base_dir'])

        print("Downloading: '" + config_data[conf_prefix + "_download_url"] + "' to: '" + download_path + "'")
        urllib.request.urlretrieve(config_data[conf_prefix + '_download_url'], download_path)
        tar = tarfile.open(download_path, "r:gz")
        tar.extractall(path=os.path.join(config_data[conf_prefix + '_base_dir']))
        tar.close()

    if conf_prefix == "zookeeper":
        config_data[conf_prefix + "_extract_dir"] = os.path.splitext(os.path.splitext(download_path)[0])[0]
    else:
        config_data[conf_prefix + "_extract_dir"] = os.path.splitext(download_path)[0]

def configure_service(service_name, conf_prefix, conf_files):
    print("Configuring service " + service_name)

    for conf_file in conf_files:
        c_in_file = os.path.join(conf_prefix, conf_file)
        c_out_file = os.path.join(config_data[conf_prefix + "_extract_dir"], conf_file)
        cf = env.get_template(c_in_file).render(config_data)
        f = open(c_out_file, "w")
        f.write(cf)
        f.close()

def install_and_start_service(service_name, conf_prefix):
    print("Installing service via systemd")

    # Create the SystemD service
    cf = env.get_template("systemd/" + conf_prefix + ".service").render(config_data)
    f = open("/etc/systemd/system/" + conf_prefix + ".service", "w")
    f.write(cf)
    f.close()

    # enable and start that service
    print("Systemctl daemon reload")
    os.system('systemctl daemon-reload')

    print("Enabling SystemD service")
    os.system('systemctl enable ' + conf_prefix)

    print("Starting SystemD service")
    os.system('systemctl start ' + conf_prefix)

def test_kafka_install():
    kafka_list_topics = os.join(os.join(config_data["kafka_extract_dir"], "bin"), "kafka-topics.sh --list --zookeeper localhost:2181")
    stream = os.popen(kafka_list_topics)
    resp = stream.read()
    print("List topic resp: " + str(resp))

def seed_data():
    print("Data will be seeded to Kafka if configured for that to happen")

if __name__ == "__main__":
    # Prepare environment
    env_prep()
    # Install Zookeeper
    download_and_extract("Zookeeper", "zookeeper")
    # Install Kafka
    download_and_extract("Kafka", "kafka")
    # Configure Zookeeper
    configure_service("Zookeeper", "zookeeper", ['conf/zoo.cfg', 'conf/log4j.properties'])
    # Configure Kafka
    configure_service("Kafka", "kafka", ['config/server.properties'])
    # Install and start Zookeeper
    install_and_start_service("Zookeeper", "zookeeper")
    # Install and start Kafka
    install_and_start_service("Kafka", "kafka")
    # Test Kafka install
    test_kafka_install()
    # Seed Kafka data
    seed_data()