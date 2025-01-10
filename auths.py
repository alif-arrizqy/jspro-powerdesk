from flask_httpauth import HTTPTokenAuth, HTTPBasicAuth

token_auth = HTTPTokenAuth(scheme='Bearer')
basic_auth = HTTPBasicAuth()
tokens = {
    'd1587d98aa2348b600edc7e7569e3997': 'noc'
}

users = {
    'teknisi': {'password': 'Joulestore2020'},
    'apt': {'password': 'apt2025'},
}

@token_auth.verify_token
def verify_token(token):
    if token in tokens:
        return tokens[token]


@basic_auth.verify_password
def verify_password(username, password):
    if username == 'teknisi' and password == 'Joulestore2020':
        return username
    if username == 'apt' and password == 'apt2025':
        return username
    return None

