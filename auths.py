from flask_httpauth import HTTPTokenAuth, HTTPBasicAuth

token_auth = HTTPTokenAuth(scheme='Bearer')
basic_auth = HTTPBasicAuth()
tokens = {
    'RUNDIEpTUFJPIEJBS1RJIDIwMTk=': 'noc'
}

users = {
    'teknisi': {'password': 'Joulestore2020'},
    'apt': {'password': 'powerapt'},
}

@token_auth.verify_token
def verify_token(token):
    if token in tokens:
        return tokens[token]


@basic_auth.verify_password
def verify_password(username, password):
    if username == 'teknisi' and password == 'Joulestore2020':
        return username
    if username == 'apt' and password == 'powerapt':
        return username
    return None
