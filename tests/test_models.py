from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from viralpanel.database import Base
from viralpanel.models import Asset, PipelineRun, Publication, Script, SourceVideo


def test_relationships():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        v = SourceVideo(url="https://t.co/1", metrics={"views": 10})
        sc = Script(source_video=v, script_text="x")
        a = Asset(script=sc, asset_type="final", file_path="f.mp4")
        p = Publication(asset=a, platform="tiktok")
        r = PipelineRun()
        s.add_all([v, sc, a, p, r])
        s.commit()
        assert v.scripts[0].assets[0].publications[0].platform == "tiktok"
        assert r.status == "running"
