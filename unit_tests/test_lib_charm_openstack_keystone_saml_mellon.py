# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import print_function

import mock

import charms_openstack.test_utils as test_utils

import charm.openstack.keystone_saml_mellon as keystone_saml_mellon


def FakeConfig(init_dict):

    def _config(key=None):
        return init_dict[key] if key else init_dict

    return _config


def FakeResourceGet(init_dict):

    def _config(key=None):
        return init_dict[key] if key else init_dict

    return _config


class Helper(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(
            keystone_saml_mellon.KeystoneSAMLMellonCharm.release)

        self.patch_object(keystone_saml_mellon, 'unitdata',
                          new=mock.MagicMock())
        self.kv = mock.MagicMock()
        self.unitdata.kv.return_value = self.kv

        self.patch_object(keystone_saml_mellon.os_utils, 'os_release',
                          new=mock.MagicMock())

        self.idp_name = "samltest"
        self.protocol_name = "mapped"
        self.user_facing_name = "samltest.id"
        self.nameid_formats = "fake:name:id:format1,fake:name:id:format2"
        self.test_config = {
            "idp-name": self.idp_name,
            "protocol-name": self.protocol_name,
            "user-facing-name": self.user_facing_name,
            "nameid-formats": self.nameid_formats,
            "subject-confirmation-data-address-check": False
        }
        self.resources = {
            "idp-metadata": "/path/to/idp-metadata.xml",
            "sp-private-key": "/path/to/sp-private-key.pem",
            "sp-signing-keyinfo": "/path/to/sp-signing-keyinfo.xml"
        }
        self.patch_object(keystone_saml_mellon.hookenv, 'config',
                          side_effect=FakeConfig(self.test_config))
        self.patch_object(keystone_saml_mellon.hookenv, 'resource_get',
                          side_effect=FakeResourceGet(self.resources))
        self.patch_object(
            keystone_saml_mellon.hookenv, 'application_version_set')
        self.patch_object(keystone_saml_mellon.hookenv, 'status_set')
        self.patch_object(keystone_saml_mellon.ch_host, 'mkdir')
        self.patch_object(keystone_saml_mellon.core.templating, 'render')

        self.template_loader = mock.MagicMock()
        self.patch_object(keystone_saml_mellon.os_templating, 'get_loader',
                          return_value=self.template_loader)
        self.patch_object(
            keystone_saml_mellon.KeystoneSAMLMellonCharm,
            'application_version',
            return_value="1.0.0")

        self.patch_object(
            keystone_saml_mellon.KeystoneSAMLMellonCharm, 'render_configs')
        self.patch_object(keystone_saml_mellon, 'os')
        self.patch_object(keystone_saml_mellon, 'subprocess')

        self.patch(
            "builtins.open", new_callable=mock.mock_open(), name="open")
        self.file = mock.MagicMock()
        self.fileobj = mock.MagicMock()
        self.fileobj.__enter__.return_value = self.file
        self.open.return_value = self.fileobj


class TestKeystoneSAMLMellonUtils(Helper):

    def test_select_release(self):
        self.kv.get.return_value = 'mitaka'
        self.assertEqual(
            keystone_saml_mellon.select_release(), 'mitaka')

        self.kv.get.return_value = None
        self.os_release.return_value = 'rocky'
        self.assertEqual(
            keystone_saml_mellon.select_release(), 'rocky')


class TestKeystoneSAMLMellonConfigurationAdapter(Helper):

    def setUp(self):
        super().setUp()
        self.hostname = "keystone-sp.local"
        self.port = "5000"
        self.tls_enabled = True
        self.unitdata_data = {
            "hostname": self.hostname,
            "port": self.port,
            "tls-enabled": self.tls_enabled,
        }
        self.kv.get.side_effect = FakeConfig(self.unitdata_data)
        self.base_url = "https://{}:{}".format(self.hostname, self.port)

    def test_validation_errors(self):
        errors = {"idp-metadata": "Bad XML"}
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        ksmca._validation_errors = errors
        self.assertEqual(ksmca.validation_errors, errors)

    def test_remote_id_attribute(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(ksmca.remote_id_attribute, "MELLON_IDP")

    def test_idp_metadata_file(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.idp_metadata_file, keystone_saml_mellon.IDP_METADATA)

    def test_sp_metadata_file(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_metadata_file, keystone_saml_mellon.SP_METADATA)

    def test_sp_private_key_file(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_private_key_file, keystone_saml_mellon.SP_PRIVATE_KEY)

    def test_keystone_host(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(ksmca.keystone_host, self.hostname)

    def test_keystone_port(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(ksmca.keystone_port, self.port)

    def test_keystone_tls_enabled(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(ksmca.tls_enabled, self.tls_enabled)

    def test_keystone_base_url(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(ksmca.keystone_base_url, self.base_url)

    def test_sp_idp_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_idp_path,
            '/v3/OS-FEDERATION/identity_providers/{}'.format(self.idp_name))

    def test_sp_protocol_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_protocol_path,
            '{}/protocols/{}'.format(ksmca.sp_idp_path, self.protocol_name))

    def test_sp_auth_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_auth_path, '{}/auth'.format(ksmca.sp_protocol_path))

    def test_mellon_endpoint_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.mellon_endpoint_path, '{}/mellon'.format(ksmca.sp_auth_path))

    def test_websso_auth_idp_protocol_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.websso_auth_idp_protocol_path,
            ('/v3/auth/OS-FEDERATION/identity_providers/{}/protocols/{}/websso'
             .format(self.idp_name, self.protocol_name)))

    def test_sp_post_response_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_post_response_path,
            '{}/postResponse'.format(ksmca.mellon_endpoint_path))

    def test_sp_logout_path(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_logout_path,
            '{}/logout'.format(ksmca.mellon_endpoint_path))

    def test_sp_auth_url(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_auth_url,
            '{}{}'.format(ksmca.keystone_base_url, ksmca.sp_auth_path))

    def test_sp_logout_url(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_logout_url,
            '{}{}'.format(ksmca.keystone_base_url, ksmca.sp_logout_path))

    def test_sp_post_response_url(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.sp_post_response_url,
            '{}{}'.format(ksmca.keystone_base_url,
                          ksmca.sp_post_response_path))

    def test_mellon_subject_confirmation_data_address_check(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.mellon_subject_confirmation_data_address_check,
            'Off')

    def test_supported_nameid_formats(self):
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        self.assertEqual(
            ksmca.supported_nameid_formats, self.nameid_formats.split(","))

    def test_idp_metadata(self):
        self.os.path.exists.return_value = True
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        # Valid XML
        self.idp_metadata_xml = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<EntityDescriptor  entityID='https://samltest.id/saml/idp'> "
            "</EntityDescriptor>")
        self.file.read.return_value = self.idp_metadata_xml
        self.assertEqual(ksmca.idp_metadata, self.idp_metadata_xml)
        self.open.assert_called_with(self.resources["idp-metadata"])

        # Inalid XML
        ksmca._idp_metadata = None
        self.file.read.return_value = "INVALID XML"
        self.assertEqual(ksmca.idp_metadata, "")
        self.assertEqual(
            ksmca._validation_errors,
            {"idp-metadata": ksmca.IDP_METADATA_INVALID})

    def test_sp_signing_keyinfo(self):
        self.os.path.exists.return_value = True
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        # Valid XML
        self.sp_signing_keyinfo_xml = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<ds:KeyInfo xmlns:ds='http://www.w3.org/2000/09/xmldsig#'>"
            "<ds:X509Data> <ds:X509Certificate> </ds:X509Certificate>"
            "</ds:X509Data> </ds:KeyInfo>")
        self.file.read.return_value = self.sp_signing_keyinfo_xml
        self.assertEqual(ksmca.sp_signing_keyinfo, self.sp_signing_keyinfo_xml)
        self.open.assert_called_with(self.resources["sp-signing-keyinfo"])

        # Inalid XML
        ksmca._sp_signing_keyinfo = None
        self.file.read.return_value = "INVALID XML"
        self.assertEqual(ksmca.sp_signing_keyinfo, "")
        self.assertEqual(
            ksmca._validation_errors,
            {"sp-signing-keyinfo": ksmca.SP_SIGNING_KEYINFO_INVALID})

    def test_sp_private_key(self):
        self.os.path.exists.return_value = True
        ksmca = keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter()
        # Valid Key
        self.sp_private_key_pem = ("""
-----BEGIN RSA PRIVATE KEY-----
MIIBPAIBAAJBANLUtlT9JMQ/RcGEipW6MBtUoFBGMOclUmOpP1BbaFJoBn19J0UG
STj29M9nDLDRdfP0O/JiisG6ejxmO0A0xTsCAwEAAQJBAKT0IKRmW3ngN2etl/CF
+FWp5LRp9qEjJk8rgIoSupCdvuT0Q6XLk/ygHeiBYcKTf2pT/PWjQxg1pD7So5K8
YcECIQD5SKfItJ5YC9mD+6H28UqQATPehRPhQEEFIl/lJCrFgwIhANiC14XvcuWc
xMy1Lcc5lFkrB+b+oWVKJyMpNTHgXivpAiEAqh0FurZfNDBp8GJgpbcFrf3UGq7v
4RBLDqjljeY/decCIEk3/lDCCFYULQ2ZW9Da7Qs2nSaGB+isKg4e+mlSmiY5AiEA
lAoUNjDHWBOlyXziqZiufMURqbPPbRkEjWwN8G2r15A=
-----END RSA PRIVATE KEY-----
            """)
        self.file.read.return_value = self.sp_private_key_pem
        self.assertEqual(ksmca.sp_private_key, self.sp_private_key_pem)
        self.open.assert_called_with(self.resources["sp-private-key"])

        # Invalid Key
        ksmca._sp_private_key = None
        self.file.read.return_value = "INVALID PEM KEY"
        self.assertEqual(ksmca.sp_private_key, '')
        self.assertEqual(
            ksmca._validation_errors,
            {"sp-private-key": ksmca.SP_PRIVATE_KEY_INVALID})


class TestKeystoneSAMLMellonCharm(Helper):

    def setUp(self):
        super().setUp()
        self.patch_object(
            keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter,
            'idp_metadata')
        self.patch_object(
            keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter,
            'sp_private_key')
        self.patch_object(
            keystone_saml_mellon.KeystoneSAMLMellonConfigurationAdapter,
            'sp_signing_keyinfo')
        self.idp_metadata.return_value = self.resources["idp-metadata"]
        self.idp_metadata.__bool__.return_value = True
        self.sp_private_key.return_value = self.resources["sp-private-key"]
        self.sp_private_key.__bool__.return_value = True
        self.sp_signing_keyinfo.return_value = self.resources[
            "sp-signing-keyinfo"]
        self.sp_signing_keyinfo.__bool__.return_value = True

    def test_configuration_complete(self):
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        self.assertTrue(ksm.configuration_complete())

        # One option not ready
        self.sp_signing_keyinfo.__bool__.return_value = False
        self.assertFalse(ksm.configuration_complete())

    def test_assess_status(self):
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        ksm.assess_status()
        self.application_version_set.asert_called_once_with()
        self.status_set.assert_called_once_with("active", "Unit is ready")

        # One option not ready
        self.status_set.reset_mock()
        self.sp_signing_keyinfo.__bool__.return_value = False
        ksm.options._validation_errors = {"idp-metadata": "malformed"}
        ksm.assess_status()
        self.status_set.assert_called_once_with(
            "blocked", "Configuration is incomplete. idp-metadata: malformed")

    def test_render_config(self):
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        ksm.render_config()
        self.assertEqual(self.render_configs.call_count, 1)
        self.assertEqual(self.render.call_count, 2)

    def test_remove_config(self):
        self.os.path.exists.return_value = True
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        ksm.remove_config()
        self.assertEqual(self.os.path.exists.call_count, 4)
        self.assertEqual(self.os.unlink.call_count, 4)

    def test_enable_module(self):
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        ksm.enable_module()
        self.subprocess.check_call.assert_called_once_with(
            ['a2enmod', 'auth_mellon'])

    def test_disable_module(self):
        ksm = keystone_saml_mellon.KeystoneSAMLMellonCharm()
        ksm.disable_module()
        self.subprocess.check_call.assert_called_once_with(
            ['a2dismod', 'auth_mellon'])
