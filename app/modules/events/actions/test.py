
def test(trigger, action):
    print("\nTest Action Result: ", action.config["result"])
    if action.config["result"] == "error":
        raise Exception("test_error")
