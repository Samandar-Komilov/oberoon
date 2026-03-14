from oberoon.routing import compile_path


class TestCompilePath:
    def test_static_path(self):
        pattern, param_types = compile_path("/hello")
        assert pattern.match("/hello")
        assert not pattern.match("/hello/extra")
        assert not pattern.match("/other")
        assert param_types == {}

    def test_str_param(self):
        pattern, param_types = compile_path("/items/{name}")
        m = pattern.match("/items/widget")
        assert m and m.groupdict() == {"name": "widget"}
        assert param_types == {"name": str}

    def test_str_param_no_slash(self):
        pattern, _ = compile_path("/items/{name}")
        assert not pattern.match("/items/a/b")

    def test_int_param(self):
        pattern, param_types = compile_path("/users/{user_id:int}")
        m = pattern.match("/users/42")
        assert m and m.groupdict() == {"user_id": "42"}
        assert param_types == {"user_id": int}

    def test_int_param_rejects_alpha(self):
        pattern, _ = compile_path("/users/{user_id:int}")
        assert not pattern.match("/users/abc")

    def test_path_param(self):
        pattern, param_types = compile_path("/files/{filepath:path}")
        m = pattern.match("/files/a/b/c.txt")
        assert m and m.groupdict() == {"filepath": "a/b/c.txt"}
        assert param_types == {"filepath": str}

    def test_multiple_params(self):
        pattern, param_types = compile_path("/orgs/{org}/repos/{repo_id:int}")
        m = pattern.match("/orgs/acme/repos/99")
        assert m and m.groupdict() == {"org": "acme", "repo_id": "99"}
        assert param_types == {"org": str, "repo_id": int}

    def test_root_path(self):
        pattern, _ = compile_path("/")
        assert pattern.match("/")
        assert not pattern.match("/anything")

    def test_exact_match_only(self):
        pattern, _ = compile_path("/hello")
        assert not pattern.match("/hello/")
        assert not pattern.match("/helloo")
        assert not pattern.match("/hell")
