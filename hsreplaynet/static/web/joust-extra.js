var JoustExtra = {
	_options: {
		hearthstonejson: null,
		locale: "enUS",
	},

	flags: {
		cards: {
			fetched_any: false,
			fetched_latest: false,
			cached: false,
			has_build: false,
			failed_any: false,
			failed_totally: false,
		}
	},

	setup: function (options) {
		Object.keys(options).forEach(function (k) {
			this._options[k] = options[k];
		}.bind(this));
		return this;
	},

	metadata: function (buildNumber, callback) {
		buildNumber = +buildNumber;

		var parse = function(result) {
			this.flags.cards.fetched_any = true;
			callback(JSON.parse(result));
		}.bind(this);

		var fetchLatest = function () {
			this._fetchMetadata("latest", function (result) {
				this.flags.cards.fetched_latest = true;
				parse(result);
			}.bind(this));
		}.bind(this);

		if (buildNumber) {
			var key = "hsjson-build-" + buildNumber;
			this.flags.cards.has_build = true;

			// check for availablity
			if (typeof(Storage) !== "undefined") {
				// check if already exists
				if (typeof localStorage[key] === "string") {
					var result = JSON.parse(localStorage[key]);
					if (typeof result === "object" && +result.length > 0) {
						this.flags.cards.cached = true;
						callback(result);
						return;
					}
				}

				// clear invalid data
				if (typeof localStorage[key] !== "undefined") {
					console.warn("Removing invalid card data in local storage");
					localStorage.removeItem(key);
				}
			}

			// fetch data
			this._fetchMetadata(buildNumber,
				function (result) {
					// success
					parse(result);

					// save to storage
					if (key != null && typeof(Storage) !== "undefined") {
						localStorage.setItem(key, result);
					}
				},
				fetchLatest
			);
		}
		else {
			fetchLatest();
		}
	},

	_fetchMetadata: function (buildNumber, successCallback, errorCallback) {
		if (!this._options.hearthstonejson) {
			throw new Error('HearthstoneJSON url was not supplied');
		}
		var url = this._options.hearthstonejson.replace(/%\(build\)s/, buildNumber).replace(/%\(locale\)s/, this._options.locale);
		$.ajax(url, {
			type: "GET",
			dataType: "text",
			success: successCallback,
			error: function (xhr, status, error) {
				if (!xhr.status) {
					// request was probably cancelled
					return;
				}
				this.flags.cards.failed_any = true;
				if (buildNumber != "latest") {
					this._options.logger && this._options.logger(
						"HearthstoneJSON: Error fetching build " + buildNumber + '\n"' + url + '" returned status ' + xhr.status,
						{hearthstonejson_url: url}
					);
				}
				else {
					this.flags.cards.failed_totally = true;
					throw new Error('HearthstoneJSON: Error fetching latest build\n"' + url + '" returned status ' + xhr.status);
				}
				errorCallback && errorCallback();
			}.bind(this)
		});
	},
};

JoustExtra.metadata = JoustExtra.metadata.bind(JoustExtra);
JoustExtra._fetchMetadata = JoustExtra._fetchMetadata.bind(JoustExtra);
