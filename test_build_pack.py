import copy,hashlib,json,shutil,unittest,uuid,zipfile
from pathlib import Path
from build_pack import build,safe_asset,validate_catalog

class PackTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).parent/('fixture-'+uuid.uuid4().hex);self.root.mkdir()
        self.addCleanup(self.cleanup);a=self.root/'assets/test';a.mkdir(parents=True)
        (a/'model.obj').write_text('mtllib model.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
        (a/'model.mtl').write_text('newmtl body\nKd 1 1 1\n')
        self.p={'format':1,'id':'bb-arcade','version':'0.1.0','cabinets':[
            {'id':'test','name':'Test cabinet','status':'authoring','backend':'fbneo','rom':'test.zip',
             'footprint':[1,1],'world_units_per_metre':40,'screen_aspect':[4,3],
             'model':'assets/test/model.obj','material':'assets/test/model.mtl'}]}
    def cleanup(self):
        root=self.root.resolve();assert root.parent==Path(__file__).parent.resolve() and root.name.startswith('fixture-')
        shutil.rmtree(root)
    def run_build(self):
        (self.root/'catalog.json').write_text(json.dumps(self.p));return build(self.root,self.root/'dist')
    def test_deterministic(self):
        self.run_build();first=(self.root/'dist/BB-Arcade.zip').read_bytes();self.run_build()
        self.assertEqual(first,(self.root/'dist/BB-Arcade.zip').read_bytes())
        d=json.loads((self.root/'dist/BB-Arcade.json').read_text())
        self.assertEqual(d['repository'],'DexOfTheWild/BB-Arcade');self.assertEqual(d['sha256'],hashlib.sha256(first).hexdigest())
        with zipfile.ZipFile(self.root/'dist/BB-Arcade.zip') as z:self.assertEqual(set(z.namelist()),{'pack.json','assets/test/model.obj','assets/test/model.mtl'})
    def test_no_binaries_roms_or_scripts(self):
        for ext in ('.zip','.7z','.exe','.dll','.py','.inc','.bin'):
            f=self.root/('assets/test/forbidden'+ext);f.write_bytes(b'fixture')
            with self.assertRaises(ValueError):self.run_build()
            f.unlink()
    def test_paths(self):
        for p in ('assets/../bad.obj','assets//bad.obj','/assets/x.obj','assets/con.obj','assets/A.obj','assets/a\\x.obj','assets/x./a.obj','assets/lpt1/a.obj'):
            self.assertFalse(safe_asset(p),p)
    def test_missing_dependency(self):
        (self.root/'assets/test/model.mtl').write_text('newmtl x\nmap_Kd missing.png\n')
        with self.assertRaises(ValueError):self.run_build()
    def test_traversal_dependency(self):
        (self.root/'assets/test/model.obj').write_text('mtllib ../../model.mtl\n')
        with self.assertRaises(ValueError):self.run_build()
    def test_authoring_cannot_register(self):
        for k in ('adapter','furniture_id','content_id'):
            p=copy.deepcopy(self.p);p['cabinets'][0][k]=1
            with self.assertRaises(ValueError):validate_catalog(p)
    def test_duplicate_native_ids(self):
        c=self.p['cabinets'][0];c.update(status='integrated',adapter='test',furniture_id=1371,content_id=1,body=c['model'],screen=c['model'])
        self.run_build();other=copy.deepcopy(c);other['id']='other';other['adapter']='other'
        # Keep paths under their own key, then verify duplicate runtime identity.
        for k in ('model','material','body','screen'):other[k]=other[k].replace('/test/','/other/')
        self.p['cabinets'].append(other)
        with self.assertRaises(ValueError):validate_catalog(self.p)
    def test_png_bounds(self):
        header=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'
        image=self.root/'assets/test/atlas.png'
        for size,valid in ((1254,True),(4096,True),(4097,False),(0,False)):
            image.write_bytes(header+size.to_bytes(4,'big')*2+b'\x08\x02\0\0\0'+b'fakecrc')
            if valid:self.run_build()
            else:
                with self.assertRaises(ValueError):self.run_build()
    def test_no_nonfinite_geometry(self):
        (self.root/'assets/test/model.obj').write_text('v nan 0 0\n')
        with self.assertRaises(ValueError):self.run_build()
    def test_boolean_not_native_number(self):
        for field,value in (('footprint',[True,1]),('screen_aspect',[4,True]),('world_units_per_metre',True)):
            p=copy.deepcopy(self.p);p['cabinets'][0][field]=value
            with self.assertRaises(ValueError):validate_catalog(p)
    def test_actual_catalog(self):
        root=Path(__file__).parent;pack=build(root,self.root/'actual')
        self.assertEqual(len(pack['cabinets']),len(json.loads((root/'catalog.json').read_text())['cabinets']))
        self.assertGreaterEqual(sum(c['status']=='integrated' for c in pack['cabinets']),6)
        self.assertTrue(all(f['path'].startswith('assets/') for f in pack['files']))

if __name__=='__main__':unittest.main()
