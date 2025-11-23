from flask import render_template


def register_error_handlers(app):
    """Register error handlers for the Flask application."""
    
    ERROR_MESSAGES = {
        # 4xx Client Errors
        400: "Bad Request - The server cannot process your request due to malformed syntax.",
        401: "Unauthorized - Authentication is required to access this resource.",
        403: "Forbidden - You don't have permission to access this resource.",
        404: "Not Found - The requested resource could not be found.",
        405: "Method Not Allowed - The HTTP method is not allowed for this resource.",
        406: "Not Acceptable - The requested resource cannot generate acceptable content.",
        408: "Request Timeout - The server timed out waiting for the request.",
        409: "Conflict - The request conflicts with the current state of the server.",
        410: "Gone - The requested resource is no longer available.",
        411: "Length Required - Content length header is required.",
        412: "Precondition Failed - Server prerequisites are not met.",
        413: "Payload Too Large - Request entity exceeds server limits.",
        414: "URI Too Long - The requested URL is too long.",
        415: "Unsupported Media Type - The media format is not supported.",
        416: "Range Not Satisfiable - Requested range is not available.",
        417: "Expectation Failed - Server cannot meet request expectations.",
        418: "I'm a teapot - Server refuses to brew coffee with a teapot.",
        421: "Misdirected Request - Request was directed at a server unable to produce a response.",
        422: "Unprocessable Entity - Request is well-formed but cannot be processed.",
        423: "Locked - The resource is locked.",
        424: "Failed Dependency - Request failed due to failure of a previous request.",
        428: "Precondition Required - The origin server requires the request to be conditional.",
        429: "Too Many Requests - Too many requests in a given amount of time.",
        431: "Request Header Fields Too Large - Header fields are too large.",
        451: "Unavailable For Legal Reasons - Resource unavailable for legal reasons.",

        # 5xx Server Errors
        500: "Internal Server Error - An unexpected condition was encountered.",
        501: "Not Implemented - The server does not support the functionality required.",
        502: "Bad Gateway - The server received an invalid response from the upstream server.",
        503: "Service Unavailable - The server is temporarily unable to handle the request.",
        504: "Gateway Timeout - The upstream server failed to respond in time.",
        505: "HTTP Version Not Supported - The HTTP version is not supported.",
    }

    def handle_error(error):
        """Generic error handler for all HTTP errors."""
        error_code = getattr(error, 'code', 500)
        error_message = ERROR_MESSAGES.get(error_code, "An unexpected error occurred.")
        return render_template('error.html', 
                               error_code=error_code,
                               error_message=error_message), error_code

    # Register handlers for all 4xx and 5xx error codes
    for error_code in ERROR_MESSAGES.keys():
        app.register_error_handler(error_code, handle_error)
    