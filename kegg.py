# kegg.py
# database_access_code.py consolodated into a module
# requires: urllib3

import urllib3;
import re;

http = urllib3.PoolManager();

#direct simply joins the array with slashes and sends request to kegg
def direct(arg_list):
	request = "http://rest.kegg.jp/"
	request += "/".join(arg_list);
	response = http.request('GET', request).data.decode() #decode() turns it into string
	return(response);

def list2(database):
	newstr = direct(['list', database]);
	newlist = newstr.split('\n');
	retlist = newlist.copy(); #for preallocation
	for i in range( len(newlist) ):
		retlist[i] = newlist[i].split('\t');
	return(retlist);   #returns list of lists
		
def find(datatype):
	newstr = str(http.request('GET', 'http://rest.kegg.jp/find/{datatype}/'.format(datatype=datatype)).data)
	newstr = newstr.replace("\\t", "\t");
	newlist = newstr.split('\\n');
	newlist[0] = newlist[0][2:]; #shave off trash at beggining of first element
	del newlist[len(newlist)-1]; #shave off last element (trash)
	return(newlist);

def find2(database, query): #this is used in cli
	newstr = direct(['find', database, query])
	#newstr = newstr.replace("\\t", "\t");
	newlist = newstr.split("\n");
	newlist[0] = newlist[0][2:]; #shave off trash at beggining of first element
	del newlist[len(newlist)-1]; #shave off last element (trash)
	return(newlist);

def get(query):
	text = direct(['get', query]);
	text = text.replace("\\t", "\t");
	text = text.replace("\\n", "\n");
	#text = text[2:len(text)-1]; #rm first 2 and last characters (trash)
	return(text)

def info(database):
	text = direct(['info', database]);
	text = text.replace("\\t", "\t");
	text = text.replace("\\n", "\n");
	text = text[2:len(text)-1]; #rm first 2 and last characters (trash)
	return(text)

#def conv(two_ids)
#       text = direct(['conv', two_ids[0], two_ids[1]]);
		
def link(database, query):
	temptext = direct(['link', database, query])
	templist = temptext.split('\n')
	retlist = templist.copy();  #preallocate
	for i in range(len(templist)):
		retlist[i] = templist[i].split('\t')[1]
	return(retlist);

#get_extract returns a dictionary containing any info
#provided in from a get command
#i.e.: get/md:M00377 => { "ENTRY":M00377, "NAME":"Reductive ... "REACTION":{"rnxxx":[[a,b][c,d]]}}
#THIS ONLY ENTERS THE FIRST ENTRY FOR SOME REASON 
def get_extract(query):
	to_parse = get(query);
	lines = to_parse.splitlines();	
	ret = {};

	while '' in lines:
		lines.remove('')
	 
	blocks = [];
	j = -1;
	i = 0;
	while i < len(lines): #parse keys and blocks
		if lines[i] == '///':
			break;
		elif re.match(r'\s', lines[i], 0).group(0) == lines[i][0]: #if first character is a space
			blocks[j] += lines[i] #concat strings
		else:
			j += 1; #start next blocks array element
			temparray = lines[i].split(); 
			ret[temparray[0]] = j;
			blocks[j] = temparray[1:]
			if ret[lines[i]] == "ENTRY":
				tokens = blocks[j].split()
				ret[lines[i]] = tokens[1];
				ret["TYPE"] = tokens[2:];
		i += 1;
		
	for key in ret.keys(): #parse blocks into structured dicts
		block = blocks[ret[key]]
		if key == '///': #shouldnt occur
			break;
		elif key == "ENTRY":
			continue; 
		elif key == "COMPOUND":
			ret[key] = []
			lines = block.splitlines()
			for i in range(len(lines)):
				line = lines[i].strip()
				match_obj = re.match(r'(C[0-9]{5})[\s]+(.*)', line, 0);
				id = match_obj.group(1);
				name = match_obj.group(2);
				(ret[key]).append( {'ID':id, 'NAME':name} );
		elif (key == "REACTION") and ('Module' in ret["TYPE"]):
			ret[key] = [] # [{'ID':<id>, 'REACTANTS':[...], 'PRODUCTS':[...]}]
			lines = block.splitlines();
			for i in range(len(lines)): #parsing each line
				d = {'ID':'', 'REACTANTS':[], 'PRODUCTS':[] }
				line = lines[i].strip();
				tokens = line.split();
				while '' in tokens:
					tokens.remove('');
					
				if ',' in tokens[0]:
					d['ID'] = tokens[0].split(',')[0];
				else:
					d['ID'] = tokens[0];
					#doesn't consider case of RX,RY+RZ
				
				passed_arrow = False;
				j = 1;
				while j < len(tokens): #parsing each token
					if tokens[j] == '->':
						passed_arrow = True;
					elif( (not passed_arrow) and (tokens[j] != '+') ):
						d['REACTANTS'].append(tokens[j]);
					elif( passed_arrow and (tokens[j] != '+') ):
						d['PRODUCTS'].append(tokens[j])
					else:
						continue;
				
				ret[key].append(d);	
		elif (key == "REACTION") and ('Compound' in ret["TYPE"]):
			ret[key] = [];
			lines = block.splitlines();
			for each in lines:
				line = each.trim;
				tokens = line.split();
				while '' in tokens:
					tokens.remove('')
				for token in tokens:
					ret[key].append(token)
		elif (key == "EQUATION") and ('Reaction' in ret["TYPE"]):
			ret[key] = {'REACTANTS':[], 'PRODUCTS':[], 'RATIOS':[]}
			tokens = block.trim.split();
			while '' in tokens:
				tokens.remove('')
			
			passed_arrow = False;
			for token in tokens:
				if token == "<=>":
					passed_arrow = True;
				elif isdigit(token):
					ret[key]['RATIOS'].append(token);
				elif( token.startswith('C') and (not passed_arrow)):
					ret[key]['REACTANTS'].append( token );
				elif( token.startswith('C') ): #and passed_arrow (implied):
					ret[key]['PRODUCTS'].append( token );
					
		else:
			ret[ key ] = block;

	return ret;


def A2B(compoundA, compoundB, depth_limit):
	#set variable idA, ask if compoundA is correctly found
	templist = find( 'compound/{0}'.format(compoundA) );
	found = False;
	for i in range(len(templist)):
		templist2 = templist[i].split('\t')
		idA = templist2[0]
		print( 'Is your first compound also known as: {0}? [y/n]'.format(templist2[1]) )
		in_buffer = input();
		if in_buffer.upper().startswith('Y'):
			found = True;
			break;
		else:
			continue;
	if( not found ):
		print( '{0} could not be found.'.format(compoundA.capitalize()) )
		return( -1 );
	
	#set variable idB, ask if compoundB is correctly found
	templist = find( 'compound/{0}'.format(compoundB) );
	found = False;
	for i in range(len(templist)):
		templist2 = templist[i].split('\t')
		idB = templist2[0]
		print( 'Is your last compound also known as: {0}? [y/n]'.format(templist2[1]) )
		in_buffer = input();
		if in_buffer.upper().startswith('Y'):
			found = True;
			break;
		else:
			continue;
	if( not found ):
		print( '{0} could not be found.'.format( compoundB.capitalize() ) )
		return( -1 );
	
	solution = {'found':False, 'modules':[], 'reactions':[], 'enzymes':[]};
	mdlist = link("module", idA);
	if( mdlist == [] ):
		return solution; #no solution for module based search
		
	for md in mdlist:
		x = module_helper(cpdB, md, [], 0, depth_limit)
		if x[ len(x)-1 ]:
			#x is solution
			solution['found'] = True;
			solution['modules'] = x;
			break;
		else:
			#solution not found
			return( solution );
	
	for md in solution['modules']:
		md_data = get_extract(md);
		for i in md_data['REACTION']:
			r = md_data['REACTION'][i]['id']
			r_data = get_extract(r);
			solution['enzymes'].append( r_data['ENZYME'] )
			solution['reactions'].append(r)
		solution['modules'].append( md )
	
	return solution;
	
def module_helper(cpdB, module, past_modules, depth, limit):
	#print( "Trying " + str(past_modules + [module]) );
	if depth > limit:
		return [False]
	elif module in past_modules:
		return [False]
	else:
		md_data = get_extract(module);
		rxns = [];
		for i in md_data['REACTION']:
			rxns = rxns + [ md_data['REACTION'][i]['id'] ]
			if cpdB in md_data['REACTION'][i]['PRODUCTS']:
				return [module];

		rxns = rxns.reverse(); #optimizes for assimilatory pathways
		for r in rxns:
			next_md_list = link('module', r);
			for next_module in next_md_list:
				x = [module] + module_helper(cpdB, next_module, past_modules + [module], depth+1, limit); #recurse
				if x[ len(x)-1 ]: #if last element is not False
					#found!
					return x; #returns array of modules
				else:
					continue;

		return [False]; #no solutions


def reaction_helper(cpd_start, cpdB, reaction, past_reactions, depth, limit):
	#print( "Trying " + str(past_reactions + [reaction]) );
	if depth > limit:
		return [False];
	if reaction in past_reactions:
		return [False];
	rxn_data = get_extract(reaction);
	if cpd_start not in rxn_data['EQUATION']['REACTANTS']:
		return [False];
	products = rxn_data['EQUATION']['PRODUCTS'];
	if cpdB in products:
		return [reaction];
	else:
		for p in products:
			next_rxn_list = link('reaction', p);
			for next_reaction in next_rxn_list:
				x = [reaction] + reaction_helper(p, cpdB, next_reaction, past_reactions + [reaction], depth+1, limit);
				if x[ len(x)-1 ]: #if last element not False
					return x;
				else:
					continue;
					
		return [False];

def remove_id_prefix(s):
        i = s.index(':')
        return s[(i+1):]
