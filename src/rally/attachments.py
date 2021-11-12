import base64
import os


class RallyAttachment(object):

    server = "https://rally1.rallydev.com/"
    output_root = os.path.abspath(
        os.path.join(".", "rally-to-anything", "rally", "assets")
    )

    def __init__(self, attachment):
        self._attachment = attachment

    def __getattr__(self, attribute):
        return getattr(self._attachment, attribute)

    @property
    def relative_path(self):
        return self._ref.replace(self.server, "")

    @property
    def disk_path(self):
        return os.path.join(self.output_root, self.relative_path, self.Name)

    @property
    def is_on_disk(self):
        return os.path.exists(self.disk_path)

    def cache_to_disk(self, force=False):
        if not self.is_on_disk and not force:
            os.makedirs(os.path.dirname(self.disk_path), exist_ok=True)
            with open(self.disk_path, "wb") as f:
                f.write(base64.b64decode(self._attachment.Content.Content))

        self._attachment.Content.Content = ""
        self._attachment.Content._hydrated = False
