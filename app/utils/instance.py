import uuid

# Unique ID for this specific server execution
# Moving this to a dedicated file prevents duplicate initialization issues
# when main.py is run as a script vs imported as a module.
SERVER_INSTANCE_ID = str(uuid.uuid4())
