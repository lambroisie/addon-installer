from aiohttp import ClientSession
from argparse import ArgumentParser
import asyncio
import json
import logging
import re
from tempfile import TemporaryFile
import zipfile


log = logging.getLogger(__name__)


class Updater:

    def __init__(self, noop=False, config_file='conf.json'):
        with open(config_file, 'r') as f:
            config = json.loads(f.read())
        self.addons_path = config['addons_path']
        self.addons = config['addons']
        self.noop = noop
        if self.noop:
            log.info('NOOP mode')

    async def _install_addon(self, session, addon):
        url = 'https://mods.curse.com/addons/wow/{}/download'.format(addon)
        async with session.get(url) as response:
            m = re.search(
                r'(?P<url>http:\/\/addons\.curse\.cursecdn\.com\/files\/\d+\/\d+\/(?P<version>.+)\.zip)'.format(addon),
                await response.text(),
                re.IGNORECASE
            )
        if not m:
            log.error('%s: Addon not found' % addon)
            return

        download_url = m.group('url')
        download_version = m.group('version')
        log.info('%s: Downloading from %s', addon, download_url)
        if not self.noop:
            async with session.get(download_url) as response:
                zip_data = await response.read()
            tmp = TemporaryFile()
            tmp.write(zip_data)
            z = zipfile.ZipFile(tmp)
            z.extractall(self.addons_path)
        log.info('%s: Extracting to %s', addon, self.addons_path)
        log.info('%s: Successfully updated to version %s', addon, download_version)

    async def run(self):
        tasks = []
        with ClientSession() as session:
            for addon in self.addons:
                tasks.append(asyncio.ensure_future(
                    self._install_addon(session, addon)
                ))
            await asyncio.wait(tasks)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s %(levelname)-8s %(message)s'
    )
    parser = ArgumentParser()
    parser.add_argument('-n', '--noop', action='store_true', help='Do not install')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    updater = Updater(noop=args.noop)
    loop.run_until_complete(updater.run())
    loop.close()