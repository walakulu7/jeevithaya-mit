import pymysql

# Fix version check issue
pymysql.version_info = (2, 2, 1, "final", 0)

# Configure pymysql to be used instead of MySQLdb
pymysql.install_as_MySQLdb()
