# XBMCnfoMoviesImporter
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Multipart filter idea by diamondsw
# Logo by CrazyRabbit
#
import os, re, time, datetime, platform, traceback

class xbmcnfo(Agent.Movies):
	name = 'XBMCnfoMoviesImporter'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia']
	pc = '/';

##### helper functions #####
	def DLog (self, LogMessage):
		if Prefs['debug']:
			Log (LogMessage)

	def getRelatedFile(self, videoFile, fileExtension):
		videoFileExtension = videoFile.split(".")[-1]
		videoFileBase = videoFile.replace('.' + videoFileExtension, '')
		videoFileBase = re.sub(r'(?is)\s*\-\s*(cd|dvd|disc|disk|part|pt|d)\s*[0-9]$', '', videoFileBase)
		videoFileBase = re.sub(r'(?is)\s*\-\s*(cd|dvd|disc|disk|part|pt|d)\s*[a-d]$', '', videoFileBase)
		return (videoFileBase + fileExtension)

	def getMovieNameFromFolder(self, folderpath, withYear):
		foldersplit = folderpath.split (self.pc)
		if withYear == True:
			if foldersplit[-1] == 'VIDEO_TS':
				moviename = self.pc.join(foldersplit[1:len(foldersplit)-1:]) + self.pc + foldersplit[-2]
			else:
				moviename = self.pc.join(foldersplit) + self.pc + foldersplit[-1]
			self.DLog("Moviename from folder (withYear): " + moviename)
		else:
			if foldersplit[-1] == 'VIDEO_TS':
				moviename = self.pc.join(foldersplit[1:len(foldersplit)-1:]) + self.pc + re.sub (r' \(.*\)',r'',foldersplit[-2])
			else:
				moviename = self.pc.join(foldersplit) + self.pc + re.sub (r' \(.*\)',r'',foldersplit[-1])
			self.DLog("Moviename from folder: " + moviename)
		return moviename

	def checkFilePaths(self, pathfns, ftype):
		for pathfn in pathfns:
			self.DLog("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

	def RemoveEmptyTags(self, xmltags):
		for xmltag in xmltags.iter("*"):
			if len(xmltag):
				continue
			if not (xmltag.text and xmltag.text.strip()):
				#self.DLog("Removing empty XMLTag: " + xmltag.tag)
				xmltag.getparent().remove(xmltag)
		return xmltags

	def FloatRound(self, x):
		return x + 0.5 / 2 - ((x + 0.5 / 2) % 0.5)

##### search function #####
	def search(self, results, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering search function")
		self.DLog("++++++++++++++++++++++++")

		self.pc = '\\' if platform.system() == 'Windows' else '/'

		path1 = String.Unquote(media.filename)
		folderpath = os.path.dirname(path1)
		self.DLog('folderpath: ' + folderpath)
		

		# Moviename with year from folder
		movienamewithyear = self.getMovieNameFromFolder (folderpath, True)
		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath, False)

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (movienamewithyear + '.nfo')
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (folderpath + self.pc + 'video_ts.nfo')
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (folderpath + self.pc + 'movie.nfo')
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		if nfoFiles: nfoNames.append (folderpath + self.pc + nfoFiles[0])

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in
			# them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			nfoTextLower = nfoText.lower()

			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				# Title
				try: media.name = nfoXML.xpath('title')[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Year
				try: media.year = nfoXML.xpath('year')[0].text
				except: pass
				# ID
				try:
					id = nfoXML.xpath('id')[0].text.strip()
				except:
					id=""
					pass
				if len(id) > 2:
						media.id = id
						self.DLog("ID from nfo: " + media.id)
				else:
					# if movie id doesn't exist, create
					# one based on hash of title and year
					ord3 = lambda x : '%.3d' % ord(x) 
					id = int(''.join(map(ord3, media.name+str(media.year))))
					id = str(abs(hash(int(id))))
					media.id = id
					self.DLog("ID generated: " + media.id)

				results.Append(MetadataSearchResult(id=media.id, name=media.name, year=media.year, lang=lang, score=100))
				try: Log('Found movie information in NFO file: title = ' + media.name + ', year = ' + str(media.year) + ', id = ' + media.id)
				except: pass
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")

##### update Function #####
	def update(self, metadata, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering update function")
		self.DLog("++++++++++++++++++++++++")

		self.pc = '\\' if platform.system() == 'Windows' else '/'

		parse_date = lambda s: Datetime.ParseDate(s).date()
		path1 = media.items[0].parts[0].file
		self.DLog('media file: ' + path1)
		folderpath = os.path.dirname(path1)
		self.DLog('folderpath: ' + folderpath)
		isDVD = os.path.basename(folderpath).upper() == 'VIDEO_TS'
		if isDVD: folderpathDVD = os.path.dirname(folderpath)

		# Moviename with year from folder
		movienamewithyear = self.getMovieNameFromFolder (folderpath, True)
		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath, False)

		posterData = None
		posterFilename = ""
		posterNames = []
		# Frodo
		posterNames.append (self.getRelatedFile(path1, '-poster.jpg'))
		posterNames.append (movienamewithyear + '-poster.jpg')
		posterNames.append (moviename + '-poster.jpg')
		posterNames.append (folderpath + self.pc + 'poster.jpg')
		if isDVD: posterNames.append (folderpathDVD + self.pc + 'poster.jpg')
		# Eden
		posterNames.append (self.getRelatedFile(path1, '.tbn'))
		posterNames.append (folderpath + "/folder.jpg")
		if isDVD: posterNames.append (folderpathDVD + self.pc + 'folder.jpg')
		# DLNA
		posterNames.append (self.getRelatedFile(path1, '.jpg'))
		# Others
		posterNames.append (folderpath + "/cover.jpg")
		if isDVD: posterNames.append (folderpathDVD + self.pc + 'cover.jpg')
		posterNames.append (folderpath + "/default.jpg")
		if isDVD: posterNames.append (folderpathDVD + self.pc + 'default.jpg')
		posterNames.append (folderpath + "/movie.jpg")
		if isDVD: posterNames.append (folderpathDVD + self.pc + 'movie.jpg')

		# check possible poster file locations
		posterFilename = self.checkFilePaths (posterNames, 'poster')

		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			for key in metadata.posters.keys():
				del metadata.posters[key]

		fanartData = None
		fanartFilename = ""
		fanartNames = []
		# Eden / Frodo
		fanartNames.append (self.getRelatedFile(path1, '-fanart.jpg'))
		fanartNames.append (movienamewithyear + '-fanart.jpg')
		fanartNames.append (moviename + '-fanart.jpg')
		fanartNames.append (folderpath + self.pc + 'fanart.jpg')
		if isDVD: fanartNames.append (folderpathDVD + self.pc + 'fanart.jpg')
		# Others
		fanartNames.append (folderpath + self.pc + 'art.jpg')
		if isDVD: fanartNames.append (folderpathDVD + self.pc + 'art.jpg')
		fanartNames.append (folderpath + self.pc + 'backdrop.jpg')
		if isDVD: fanartNames.append (folderpathDVD + self.pc + 'backdrop.jpg')
		fanartNames.append (folderpath + self.pc + 'background.jpg')
		if isDVD: fanartNames.append (folderpathDVD + self.pc + 'background.jpg')

		# check possible fanart file locations
		fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			for key in metadata.art.keys():
				del metadata.art[key]

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (movienamewithyear + '.nfo')
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (folderpath + self.pc + 'video_ts.nfo')
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (folderpath + self.pc + 'movie.nfo')
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		if nfoFiles: nfoNames.append (folderpath + self.pc + nfoFiles[0])

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				#remove empty xml tags
				self.DLog('Removing empty XML tags from tvshows nfo...')
				nfoXML = self.RemoveEmptyTags(nfoXML)

				# Title
				try: metadata.title = nfoXML.xpath('title')[0].text.strip()
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Year
				try: metadata.year = int(nfoXML.xpath("year")[0].text.strip())
				except: pass
				# Original Title
				try: metadata.original_title = nfoXML.xpath('originaltitle')[0].text.strip()
				except: pass
				# Rating
				try:
					rating = float(nfoXML.xpath("rating")[0].text.replace(',', '.'))
					if Prefs['fround']:
						metadata.rating = self.FloatRound(rating)
					else:
						metadata.rating = rating
				except: pass
				# Content Rating
				try:
					mpaa = nfoXML.xpath('./mpaa')[0].text.strip()
					match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
					if match.group('mpaa'):
						content_rating = match.group('mpaa')
					else:
						content_rating = 'NR'
					metadata.content_rating = content_rating
				except:
					try:
						content_rating = nfoXML.xpath('certification')[0].text.strip()
						metadata.content_rating = content_rating
					except: pass
				# Studio
				try: metadata.studio = nfoXML.xpath("studio")[0].text.strip()
				except: pass
				# Premiere
				try:
					release_string = None
					try:
						self.DLog("Reading releasedate tag...")
						release_string = nfoXML.xpath("releasedate")[0].text.strip()
						self.DLog("Releasedate tag is: " + release_string)
					except:
						self.DLog("No releasedate tag found...")
						pass
					if not release_string:
						try:
							self.DLog("Reading dateadded tag...")
							release_string = nfoXML.xpath("dateadded")[0].text.strip()
							self.DLog("Dateadded tag is: " + release_string)
						except:
							self.DLog("No dateadded tag found...")
							pass
					if release_string:
						release_date = parse_date(release_string)
				except:
					self.DLog("Exception parsing releasedate: " + traceback.format_exc())
					pass
				try:
					if not release_date:
						self.DLog("Fallback to year tag instead...")
						release_date = time.strptime(str(metadata.year) + "-01-01", "%Y-%m-%d")
						metadata.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(release_date)).date()
					else:
						self.DLog("Setting releasedate...")
						metadata.originally_available_at = release_date
				except: pass

				# Tagline
				try: metadata.tagline = nfoXML.xpath("tagline")[0].text.strip()
				except: pass
				# Summary (Outline/Plot)
				try:
					if Prefs['plot']:
						self.DLog("User setting forces plot before outline...")
						stype1 = 'plot'
						stype2 = 'outline'
					else:
						self.DLog("Default setting forces outline before plot...")
						stype1 ='outline'
						stype2 = 'plot'
					try:
						summary = nfoXML.xpath(stype1)[0].text.strip('| \t\r\n')
						if not summary:
							self.DLog("No or empty " + stype1 + " tag. Fallback to " + stype2 +"...")
							raise
					except:
						summary = nfoXML.xpath(stype2)[0].text.strip('| \t\r\n')
					metadata.summary = summary
				except:
					self.DLog("Exception on reading summary!")
					pass
				# Writers (Credits)
				try: 
					credits = nfoXML.xpath('credits')
					metadata.writers.clear()
					[metadata.writers.add(c.strip()) for creditXML in credits for c in creditXML.text.split("/")]
					metadata.writers.discard('')
				except: pass
				# Directors
				try: 
					directors = nfoXML.xpath('director')
					metadata.directors.clear()
					[metadata.directors.add(d.strip()) for directorXML in directors for d in directorXML.text.split("/")]
					metadata.directors.discard('')
				except: pass
				# Genres
				try:
					genres = nfoXML.xpath('genre')
					metadata.genres.clear()
					[metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split("/")]
					metadata.genres.discard('')
				except: pass
				# Countries
				try:
					countries = nfoXML.xpath('country')
					metadata.countries.clear()
					[metadata.countries.add(c.strip()) for countryXML in countries for c in countryXML.text.split("/")]
					metadata.countries.discard('')
				except: pass
				# Collections (Set)
				try:
					sets = nfoXML.xpath('set')
					metadata.collections.clear()
					[metadata.collections.add(s.strip()) for setXML in sets for s in setXML.text.split("/")]
					metadata.collections.discard('')
				except: pass
				# Duration
				try:
					runtime = nfoXML.xpath("runtime")[0].text.strip()
					metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
				except: pass
				# Actors
				metadata.roles.clear()
				for actor in nfoXML.xpath('actor'):
					role = metadata.roles.new()
					try: role.actor = actor.xpath("name")[0].text
					except: pass
					try: role.role = actor.xpath("role")[0].text
					except: pass
					
				# Remote posters and fanarts are disabled for now; having them seems to stop the local artworks from being used.
				#(remote) posters
				#(local) poster
				if posterData:
					metadata.posters[posterFilename] = Proxy.Media(posterData)
				#(remote) fanart
				#(local) fanart
				if fanartData:
					metadata.art[fanartFilename] = Proxy.Media(fanartData)
				
				Log("---------------------")
				Log("Movie nfo Information")
				Log("---------------------")
				try: Log("ID: " + str(metadata.guid))
				except: Log("ID: -")
				try: Log("Title: " + str(metadata.title))
				except: Log("Title: -")
				try: Log("Year: " + str(metadata.year))
				except: Log("Year: -")
				try: Log("Original: " + str(metadata.original_title))
				except: Log("Original: -")
				try: Log("Rating: " + str(metadata.rating))
				except: Log("Rating: -")
				try: Log("Content: " + str(metadata.content_rating))
				except: Log("Content: -")
				try: Log("Studio: " + str(metadata.studio))
				except: Log("Studio: -")
				try: Log("Premiere: " + str(metadata.originally_available_at))
				except: Log("Premiere: -")
				try: Log("Tagline: " + str(metadata.tagline))
				except: Log("Tagline: -")
				try: Log("Summary: " + str(metadata.summary))
				except: Log("Summary: -")
				Log("Writers:")
				try: [Log("\t" + writer) for writer in metadata.writers]
				except: Log("\t-")
				Log("Directors:")
				try: [Log("\t" + director) for director in metadata.directors]
				except: Log("\t-")
				Log("Genres:")
				try: [Log("\t" + genre) for genre in metadata.genres]
				except: Log("\t-")
				Log("Countries:")
				try: [Log("\t" + country) for country in metadata.countries]
				except: Log("\t-")
				Log("Collections:")
				try: [Log("\t" + collection) for collection in metadata.collections]
				except: Log("\t-")
				try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
				except: Log("Duration: -")
				Log("Actors:")
				try: [Log("\t" + actor.actor + " > " + actor.role) for actor in metadata.roles]
				except: [Log("\t" + actor.actor) for actor in metadata.roles]
				except: Log("\t-")
				Log("---------------------")
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")
			return metadata