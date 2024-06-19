import logging

class SendEmailClient(object):
    """ A dummy class to perform background tasks,
      in a production use case this has to register to a proper
      asynchronous task handler like (celery, rq, rabbitMQ etc)
    """
    
    def delay(self, *args, **kwargs):
        logging.info(f"Sending email with: {args, kwargs}")