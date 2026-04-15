class Database:
    def __init__(self):
        self.connection = None
        self.db = self
        
        # Cria o sqlite in-memory database
        self.connection_string = ":memory:"
        
    def status(self):
        """Get the current status of the database connection."""
        if self.db.connection:
            return "Database is connected"
        return "Database is disconnected"

    def connect(self, connection_string):
        """Establish a database connection."""
        self.connection = f"Connected to database with {connection_string}"
        return self.connection

    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection = None
            return "Disconnected from database"
        return "No active connection to disconnect"

    def execute_query(self, query):
        """Execute a database query."""
        if not self.connection:
            return "No active connection. Please connect to the database first."
        return f"Executing query: {query}"
    
class Modal:
    def __init__(self, db: Database):
        self.db = db
        self.connection_string = ""
        
    def perform_action(self, query):
        """Perform a database action by connecting, executing a query, and disconnecting."""
        connect_msg = self.db.connect(self.connection_string)
        query_result = self.db.execute_query(query)
        disconnect_msg = self.db.disconnect()
        return connect_msg, query_result, disconnect_msg
    
    def get_status(self):
        """Get the current status of the database connection."""
        if self.db.connection:
            return "Database is connected"
        return "Database is disconnected"
    
    # Crud methods
    def create(self, connection_string):
        """Create a new database connection."""
        return self.db.connect(connection_string)
    
    def read(self):
        """Read the current connection status."""
        return self.get_status()
    
    def update(self, new_connection_string):
        """Update the database connection string."""
        self.connection_string = new_connection_string
        return f"Connection string updated to: {new_connection_string}"
    
    def delete(self):
        """Delete the current database connection."""
        return self.db.disconnect()
    
class Controller:
    def __init__(self, db: Database):
        self.db = db
        
    def _transform_query(self, json_query):
        """Transform the query before execution."""
        return json_query.strip().upper()

    def run(self, connection_string, method, query):
        """Connect to the database, execute a query, and disconnect."""
        connect_msg = self.db.connect(connection_string)
        query_result = self.db.execute_query(self._transform_query(query))
        disconnect_msg = self.db.disconnect()
        return connect_msg, query_result, disconnect_msg
    
# Example usage
db = Database()
controller = Controller(db)

connection_string = "Server=localhost;Database=mydb;User Id=myuser;Password=mypassword;"
query = "select * from users"

connect_msg, query_result, disconnect_msg = controller.run(connection_string, "get", query)

print(connect_msg)
print(query_result)
print(disconnect_msg)