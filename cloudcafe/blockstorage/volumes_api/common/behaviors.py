from time import time, sleep

from cafe.engine.behaviors import BaseBehavior
from cloudcafe.common.behaviors import StatusProgressionVerifier


class VolumesAPIBehaviorException(Exception):
    pass


class VolumesAPI_CommonBehaviors(BaseBehavior):
    statuses = None

    def _verify_entity(self, resp):
        # Verify volume create call succeeded
        if not resp.ok:
            msg = "Call failed with status_code {0} ".format(resp.status_code)
            self._log.error(msg)
            raise VolumesAPIBehaviorException(msg)

        if resp.entity is None:
            msg = "Response body did not deserialize as expected"
            self._log.error(msg)
            raise VolumesAPIBehaviorException(msg)

        return resp.entity

    @staticmethod
    def _calculate_timeout(
            size=None, timeout=None, min_timeout=None, max_timeout=None,
            wait_per_gb=None):

        # Prevents comparison with None in min() and max()
        timeout = timeout or 0

        if wait_per_gb is not None and size is not None:
            timeout = timeout or size * wait_per_gb

        if min_timeout is not None:
            timeout = max(timeout, min_timeout)

        if max_timeout is not None:
            timeout = min(timeout, max_timeout)

        return timeout

    def calculate_volume_create_timeout(self, volume_size):
        timeout = self._calculate_timeout(
            size=volume_size,
            max_timeout=self.config.volume_create_max_timeout,
            min_timeout=self.config.volume_create_min_timeout,
            wait_per_gb=self.config.volume_create_wait_per_gigabyte)
        if not timeout:
            timeout = self.config.volume_create_base_timeout
        else:
            timeout += self.config.volume_create_base_timeout

        return timeout

    def calculate_snapshot_create_timeout(self, volume_size):
        timeout = self._calculate_timeout(
            size=volume_size,
            max_timeout=self.config.snapshot_create_max_timeout,
            min_timeout=self.config.snapshot_create_min_timeout,
            wait_per_gb=self.config.snapshot_create_wait_per_gigabyte)
        if not timeout:
            timeout = self.config.snapshot_create_base_timeout
        else:
            timeout += self.config.snapshot_create_base_timeout

        return timeout

    def create_volume(
            self, size, volume_type, name=None, description=None,
            availability_zone=None, metadata=None, bootable=None,
            image_ref=None, snapshot_id=None, source_volid=None):
        """This should be implemented by the inheriting class.  It's
        purpose is to hide the parameter name differences between the v1
        and v2 volumes api's for other methods in this behavior that
        also call create_volume."""
        raise NotImplementedError

    def create_snapshot(
            self, volume_id, name=None, description=None,
            force_create=False, requestslib_kwargs=None):
        """This should be implemented by the inheriting class.  It's
        purpose is to hide the parameter name differences between the v1
        and v2 volumes api's for other methods in this behavior that
        also call create_volume."""
        raise NotImplementedError

    def get_volume_status(self, volume_id):
        resp = self.client.get_volume_info(volume_id=volume_id)
        self._verify_entity(resp)
        return resp.entity.status

    def wait_for_volume_status(
            self, volume_id, expected_status, timeout, poll_rate=None):
        """ Waits for a specific status.  Raises VolumesAPIBehaviorException
        if status is not observed within timeout seconds.
        Note:  Unreliable for transient statuses like 'deleting'.
        """

        poll_rate = poll_rate or self.config.volume_status_poll_frequency
        timeout = timeout
        end_time = time() + timeout

        while time() < end_time:
            status = self.get_volume_status(volume_id)
            if status == expected_status:
                self._log.info(
                    "Expected Volume status '{0}' observed as expected".format(
                        expected_status))
                break

            sleep(poll_rate)
        else:
            msg = (
                "wait_for_volume_status() ran for {0} seconds and did not "
                "observe the volume attain the {1} status.".format(
                    timeout, expected_status))
            self._log.info(msg)
            raise VolumesAPIBehaviorException(msg)

    def get_snapshot_status(self, snapshot_id):
        resp = self.client.get_snapshot_info(snapshot_id=snapshot_id)
        self._verify_entity(resp)
        return resp.entity.status

    def wait_for_snapshot_status(
            self, snapshot_id, expected_status, timeout, poll_rate=None):
        """ Waits for a specific status and returns None when that status is
        observed.
        Note:  Unreliable for transient statuses like 'deleting'.
        """

        poll_rate = poll_rate or self.config.snapshot_status_poll_frequency
        end_time = time() + timeout

        while time() < end_time:
            resp = self.client.get_snapshot_info(snapshot_id=snapshot_id)
            self._verify_entity(resp)

            if resp.entity.status == expected_status:
                self._log.info('Expected Snapshot status "{0}" observed'
                    .format(expected_status))
                break
            sleep(poll_rate)

        else:
            msg = (
                "wait_for_snapshot_status() ran for {0} seconds and did not "
                "observe the snapshot achieving the '{1}' status.".format(
                    timeout, expected_status))
            self._log.error(msg)
            raise VolumesAPIBehaviorException(msg)

    def create_available_volume(
            self, size, volume_type, name=None, description=None,
            availability_zone=None, metadata=None, bootable=None,
            image_ref=None, snapshot_id=None, source_volid=None, timeout=None):

        metadata = metadata or {}
        timeout = timeout or self.calculate_volume_create_timeout(size)

        self._log.info("create_available_volume() is creating a volume")
        resp = self.create_volume(
            size, volume_type, name=name, description=description,
            availability_zone=availability_zone, metadata=metadata,
            bootable=bootable, image_ref=image_ref, snapshot_id=snapshot_id,
            source_volid=source_volid)

        volume = self._verify_entity(resp)
        # Verify volume progression from 'creating' to 'available'
        verifier = StatusProgressionVerifier(
            'volume', volume.id_, self.get_volume_status, volume.id_)
        verifier.add_state(
            self.statuses.Volume.CREATING,
            self.config.volume_create_min_timeout,
            self.config.volume_status_poll_frequency, 1, True)
        verifier.add_state(
            self.statuses.Volume.AVAILABLE, timeout,
            self.config.volume_status_poll_frequency, 1, False)
        verifier.start()

        # Return volume model
        return volume

    def create_available_snapshot(
            self, volume_id, name=None, description=None, force_create=True,
            timeout=None):

        # Try and get volume size to calculate minimum wait time
        vol_size = None
        if not timeout:
            try:
                resp = self.client.get_volume_info(volume_id)
                self._verify_entity(resp)
                vol_size = resp.entity.size
            except:
                # If volume size isn't available, timeout defaults to
                # a non-optimized value
                pass
        timeout = self.calculate_snapshot_create_timeout(vol_size)
        self._log.debug(
            "create_available_snapshot() timeout set to {0}".format(timeout))

        # Create the snaphsot
        self._log.info("create_available_snapshot is creating a snapshot")
        resp = self.create_snapshot(
            volume_id, force_create=force_create, name=name,
            description=description)
        self._verify_entity(resp)

        # Verify snapshot status progression
        snapshot_id = resp.entity.id_
        verifier = StatusProgressionVerifier(
            'snapshot', snapshot_id, self.get_snapshot_status, snapshot_id)
        verifier.add_state(
            self.statuses.Snapshot.CREATING,
            self.config.snapshot_create_min_timeout, 1, 1, True)
        verifier.add_state(
            self.statuses.Snapshot.AVAILABLE, timeout,
            self.conig.snapshot_status_poll_frequency, 3, False)
        verifier.start()

        return resp.entity

    def list_volume_snapshots(self, volume_id):

        resp = self.client.list_all_snapshots_info()
        self._verify_entity(resp)

        # Expects an entity of type VolumeSnapshotList
        volume_snapshots = [s for s in resp.entity if s.volume_id == volume_id]
        return volume_snapshots

    def delete_volume_confirmed(
            self, volume_id, size=None, timeout=None, poll_rate=None):
        """Returns True if volume deleted, False otherwise"""

        timeout = self._calculate_timeout(
            size=size, timeout=timeout,
            min_timeout=self.config.volume_delete_min_timeout,
            max_timeout=self.config.volume_delete_max_timeout,
            wait_per_gb=self.config.volume_delete_wait_per_gigabyte)

        poll_rate = poll_rate or self.config.volume_status_poll_frequency

        timeout_msg = (
            "delete_volume_confirmed() was unable to confirm the volume"
            "delete within the alloted {0} second timeout".format(timeout))

        end = time() + timeout
        while time() < end:
            # issue DELETE request on volume
            resp = self.client.delete_volume(volume_id)

            if not resp.ok and resp.status_code not in [404, 400]:
                msg = (
                    "delete_volume_confirmed() call to delete_volume() failed "
                    "with a '{0}'".format(resp.status_code))
                self._log.error(msg)
                return False
            else:
                break
            sleep(poll_rate)
        else:
            self._log.error(timeout_msg)
            return False

        #Contine where last timeout loop left off
        while time() < end:
            #Poll volume status to make sure it deleted properly
            status_resp = self.client.get_volume_info(volume_id)
            if status_resp.status_code == 404:
                self._log.info(
                    "Status request on volume {0} returned 404, volume delete"
                    "confirmed".format(volume_id))
                return True

            if not status_resp.ok and status_resp.status_code != 404:
                self._log.error(
                    "Status request on volume {0} failed with a {1}".format(
                        volume_id, status_resp.status_code))
                return False

            sleep(poll_rate)
        else:
            self._log.error(timeout_msg)
            return False

    def delete_snapshot_confirmed(
            self, snapshot_id, vol_size=None, timeout=None, poll_rate=None):
        """Returns True if snapshot deleted, False otherwise"""

        timeout = self._calculate_timeout(
            size=vol_size, timeout=timeout,
            min_timeout=self.config.snapshot_delete_min_timeout,
            max_timeout=self.config.snapshot_delete_max_timeout,
            wait_per_gb=self.config.snapshot_delete_wait_per_gigabyte)

        poll_rate = poll_rate or self.config.snapshot_status_poll_frequency

        timeout_msg = (
            "delete_snapshot_confirmed() was unable to confirm the snapshot "
            "deleted within the alloted {0} second timeout".format(timeout))

        end = time() + timeout
        while time() < end:
            # issue DELETE request on volume snapshot
            resp = self.client.delete_snapshot(snapshot_id)

            if not resp.ok:
                msg = (
                    "delete_snapshot_confirmed() call to delete_snapshot()"
                    "failed with a '{0}'".format(resp.status_code))
                self._log.error(msg)
                return False
            else:
                break

            sleep(poll_rate)
        else:
            self._log.error(timeout_msg)
            return False

        while time() < end:
            # Poll snapshot status to make sure it deleted properly
            status_resp = self.client.get_snapshot_info(snapshot_id)
            if status_resp.status_code == 404:
                self._log.info(
                    "Status request on snapshot {0} returned 404, snapshot"
                    "delete confirmed".format(snapshot_id))
                return True

            if not status_resp.ok and status_resp.status_code != 404:
                self._log.error(
                    "Status request on snapshot {0} failed with a {1}".format(
                        snapshot_id, resp.status_code))
                return False

            sleep(poll_rate)
        else:
            self._log.error(timeout_msg)
            return False

    def delete_volume_with_snapshots_confirmed(self, volume_id):
        """Returns True if volume deleted, False otherwise"""

        #Attempt to delete all snapshots associated with provided volume_id
        snapshots = self.list_volume_snapshots(volume_id)
        if snapshots is not None and len(snapshots) > 0:
            for snap in snapshots:
                if not self.delete_snapshot_confirmed(snap.id_):
                    self._log.warning(
                        "delete_volume_with_snapshots_confirmed() unable"
                        "to confirm delete of snapshot {0} for volume {1}."
                        "Still attempting to delete volume..."
                        .format(snap.id_, volume_id))

        if not self.delete_volume_confirmed(volume_id):
            self._log.warning(
                "delete_volume_with_snapshots_confirmed() unable to confirm"
                "delete of volume {0}.".format(volume_id))
            return False
        return True
