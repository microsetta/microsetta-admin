from ._model import Sample


class _APIRequest:
    def get(self, url):
        # TODO: replace mock with real stuff...
        if '/scan' in url:
            if '000004216' in url:
                mock = Sample('d8592c74-9699-2135-e040-8a80115d6401',
                              '2013-10-15 09:30:00', 'Stool', 'stuff',
                              '000004216', '2013-10-16',
                              ['American Gut Project'])
                return (mock.to_api(), 200)
            else:
                return ({}, 404)
        else:
            return ({}, 404)


APIRequest = _APIRequest()
